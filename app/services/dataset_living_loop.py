"""
Sistema de Loop Contínuo para Dataset Living
Atualiza automaticamente o dataset com conversas reais que geram conversão
"""
import asyncio
import schedule
import time
import logging
from datetime import datetime, timedelta
from pathlib import Path
import json
import os
import subprocess

from app.services.dataset_expander import dataset_expander
from app.services.firebase_service import firebase_service

logger = logging.getLogger(__name__)

class DatasetLivingLoop:
    """Sistema de loop contínuo para dataset vivo"""
    
    def __init__(self, 
                 check_interval_hours: int = 24,
                 min_new_conversations: int = 50,
                 auto_deploy: bool = False):
        
        self.check_interval_hours = check_interval_hours
        self.min_new_conversations = min_new_conversations
        self.auto_deploy = auto_deploy
        
        # Controle de estado
        self.last_check = datetime.utcnow() - timedelta(days=30)  # Primeira execução pega últimos 30 dias
        self.dataset_version = 1
        self.total_training_examples = 0
        
        # Paths
        self.datasets_dir = Path("datasets/living")
        self.datasets_dir.mkdir(parents=True, exist_ok=True)
        
        self.git_repo_path = Path("datasets/repo")  # Git repo para versionamento
        
    async def start_continuous_loop(self):
        """Inicia loop contínuo de atualização do dataset"""
        logger.info("🔄 Iniciando loop contínuo de dataset living...")
        
        # Agendar execuções
        schedule.every(self.check_interval_hours).hours.do(self.check_and_update_dataset)
        
        # Primeira execução imediata
        await self.check_and_update_dataset()
        
        # Loop principal
        while True:
            schedule.run_pending()
            await asyncio.sleep(3600)  # Verificar a cada hora
    
    async def check_and_update_dataset(self):
        """Verificar e atualizar dataset se necessário"""
        try:
            logger.info("🔍 Verificando novas conversas para dataset...")
            
            # 1. Buscar conversas desde último check
            new_conversations = await self._get_new_conversations()
            
            if len(new_conversations) < self.min_new_conversations:
                logger.info(f"📊 Apenas {len(new_conversations)} novas conversas (min: {self.min_new_conversations}). Aguardando mais dados.")
                return
            
            # 2. Filtrar apenas conversas com conversão
            converted_conversations = await self._filter_successful_conversations(new_conversations)
            
            if len(converted_conversations) < 10:  # Mínimo para fine-tuning
                logger.info(f"📈 Apenas {len(converted_conversations)} conversas convertidas. Aguardando mais sucessos.")
                return
            
            logger.info(f"✅ Encontradas {len(converted_conversations)} conversas convertidas!")
            
            # 3. Expandir dataset
            expanded_examples = await dataset_expander.data_augment_examples(
                converted_conversations, 
                target_multiplier=3
            )
            
            # 4. Salvar nova versão
            version_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            dataset_path = await self._save_versioned_dataset(expanded_examples, version_timestamp)
            
            # 5. Commit ao git (se configurado)
            if self.git_repo_path.exists():
                await self._commit_to_git(dataset_path, len(expanded_examples))
            
            # 6. Fazer fine-tuning automático (se habilitado)
            if self.auto_deploy:
                await self._trigger_automatic_finetune(dataset_path)
            
            # 7. Atualizar estado
            self.last_check = datetime.utcnow()
            self.dataset_version += 1
            self.total_training_examples += len(expanded_examples)
            
            logger.info(f"🎉 Dataset atualizado! Versão {self.dataset_version}, {self.total_training_examples} exemplos totais")
            
        except Exception as e:
            logger.error(f"❌ Erro no loop de dataset: {e}")
    
    async def _get_new_conversations(self) -> list:
        """Buscar conversas novas desde último check"""
        try:
            # Buscar mensagens desde último check
            raw_messages = await firebase_service.get_recent_conversations(
                since=self.last_check,
                limit=500
            )
            
            # Converter para exemplos de treinamento
            examples = []
            
            for msg in raw_messages:
                try:
                    example = dataset_expander._convert_conversation_to_example(
                        [msg], 
                        "firebase_living", 
                        msg.get('user_phone', 'unknown')
                    )
                    if example:
                        examples.append(example)
                except Exception as e:
                    logger.debug(f"Erro ao converter mensagem: {e}")
            
            return examples
        
        except Exception as e:
            logger.error(f"Erro ao buscar novas conversas: {e}")
            return []
    
    async def _filter_successful_conversations(self, conversations: list) -> list:
        """Filtrar apenas conversas que resultaram em conversão"""
        successful = []
        
        for conv in conversations:
            try:
                # Critérios de sucesso:
                # 1. Lead score alto (4-5)
                # 2. Tem intenção de agendamento
                # 3. Mensagem final do assistente sugere próximo passo
                
                if conv.lead_score >= 4 and conv.has_scheduling:
                    # Verificar se última mensagem do assistant é de qualidade
                    assistant_messages = [
                        m for m in conv.messages 
                        if m.get('role') == 'assistant'
                    ]
                    
                    if assistant_messages:
                        last_assistant_msg = assistant_messages[-1].get('content', '').lower()
                        
                        # Verificar se contém call-to-action
                        cta_keywords = [
                            'agendar', 'visita', 'quando', 'horário', 
                            'posso mostrar', 'vamos ver', 'que tal',
                            'disponível', 'marcar'
                        ]
                        
                        if any(keyword in last_assistant_msg for keyword in cta_keywords):
                            successful.append(conv)
                            logger.debug(f"Conversa bem-sucedida: {conv.conversation_id}")
            
            except Exception as e:
                logger.debug(f"Erro ao filtrar conversa: {e}")
        
        logger.info(f"🎯 {len(successful)}/{len(conversations)} conversas filtradas como sucessos")
        return successful
    
    async def _save_versioned_dataset(self, examples: list, version: str) -> str:
        """Salva dataset com versionamento"""
        
        filename = f"sofia_living_v{self.dataset_version}_{version}"
        
        # Salvar dataset expandido
        dataset_path = dataset_expander.save_expanded_dataset(examples, filename)
        
        # Salvar metadados da versão
        metadata = {
            "version": self.dataset_version,
            "timestamp": version,
            "total_examples": len(examples),
            "successful_conversations": len([e for e in examples if e.lead_score >= 4]),
            "sources": list(set([e.source for e in examples])),
            "created_from_period": {
                "start": self.last_check.isoformat(),
                "end": datetime.utcnow().isoformat()
            }
        }
        
        metadata_path = self.datasets_dir / f"{filename}.metadata.json"
        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False, default=str)
        
        logger.info(f"📁 Dataset v{self.dataset_version} salvo: {dataset_path}")
        return dataset_path
    
    async def _commit_to_git(self, dataset_path: str, examples_count: int):
        """Commit automático no git repo"""
        try:
            if not self.git_repo_path.exists():
                # Inicializar repo se não existe
                subprocess.run(['git', 'init'], cwd=self.git_repo_path, check=True)
                logger.info("📦 Git repo inicializado")
            
            # Copiar arquivo para repo
            import shutil
            repo_file = self.git_repo_path / Path(dataset_path).name
            shutil.copy2(dataset_path, repo_file)
            
            # Git add e commit
            subprocess.run(['git', 'add', '.'], cwd=self.git_repo_path, check=True)
            
            commit_msg = f"Dataset v{self.dataset_version}: +{examples_count} exemplos de conversas convertidas"
            subprocess.run(['git', 'commit', '-m', commit_msg], 
                          cwd=self.git_repo_path, check=True)
            
            logger.info(f"📝 Commit realizado: {commit_msg}")
            
        except subprocess.CalledProcessError as e:
            logger.warning(f"⚠️ Erro no git commit: {e}")
        except Exception as e:
            logger.error(f"❌ Erro no git: {e}")
    
    async def _trigger_automatic_finetune(self, dataset_path: str):
        """Dispara fine-tuning automático (madrugada)"""
        
        current_hour = datetime.now().hour
        
        # Só executar entre 2h e 5h da manhã (menor uso)
        if not (2 <= current_hour <= 5):
            logger.info(f"⏰ Fine-tuning agendado para madrugada (atual: {current_hour}h)")
            return
        
        try:
            # Script de fine-tuning
            finetune_script = f"""
import openai
import json

# Configurar OpenAI
openai.api_key = "{os.getenv('OPENAI_API_KEY')}"

# Fazer upload do dataset
with open("{dataset_path}", "rb") as f:
    response = openai.File.create(
        file=f,
        purpose="fine-tune"
    )
    file_id = response["id"]

# Criar fine-tune job
job = openai.FineTune.create(
    training_file=file_id,
    model="gpt-3.5-turbo",  # ou gpt-4 se disponível
    n_epochs=3,
    learning_rate_multiplier=0.3,
    batch_size=8,
    suffix=f"sofia_v{self.dataset_version}"
)

print(f"Fine-tune job criado: {{job['id']}}")

# Salvar job ID para monitoramento
with open("finetune_jobs.json", "a") as f:
    json.dump({{
        "job_id": job["id"],
        "dataset_version": {self.dataset_version},
        "created_at": "{datetime.utcnow().isoformat()}",
        "dataset_path": "{dataset_path}"
    }}, f)
    f.write("\\n")
"""
            
            # Executar script
            exec(finetune_script)
            logger.info(f"🚀 Fine-tuning automático disparado para v{self.dataset_version}")
            
        except Exception as e:
            logger.error(f"❌ Erro no fine-tuning automático: {e}")
    
    def get_status(self) -> dict:
        """Status atual do sistema"""
        return {
            "active": True,
            "dataset_version": self.dataset_version,
            "total_examples": self.total_training_examples,
            "last_check": self.last_check.isoformat(),
            "check_interval_hours": self.check_interval_hours,
            "auto_deploy": self.auto_deploy,
            "next_check": (self.last_check + timedelta(hours=self.check_interval_hours)).isoformat()
        }

# Instância global
dataset_living_loop = DatasetLivingLoop(
    check_interval_hours=int(os.getenv("DATASET_UPDATE_HOURS", "24")),
    min_new_conversations=int(os.getenv("MIN_NEW_CONVERSATIONS", "50")),
    auto_deploy=os.getenv("AUTO_FINETUNE", "false").lower() == "true"
)