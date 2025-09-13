"""
Chatbot Inteligente para Análise de Imóveis
Integra o PropertyImageAnalyzer com interface de chat
"""

import asyncio
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
import json
import os
import base64
import aiohttp
import socket

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PropertyImageAnalyzer:
    def __init__(self, deployment_token: str, deployment_id: str):
        self.deployment_token = deployment_token
        self.deployment_id = deployment_id
        self.abacus_api_key = os.getenv("ABACUS_API_KEY", "")
        
        if not self.abacus_api_key:
            logger.warning("ABACUS_API_KEY não configurado - análise de imagem não funcionará")
        else:
            logger.info(f"ABACUS_API_KEY configurado: {self.abacus_api_key[:10]}...")

    async def test_dns_connectivity(self) -> bool:
        """Testa conectividade DNS e rede com Abacus"""
        try:
            # Teste DNS
            host = "apps.abacus.ai"
            logger.info(f"Testando DNS para {host}...")
            
            # Resolver DNS
            try:
                ip = socket.gethostbyname(host)
                logger.info(f"DNS OK: {host} -> {ip}")
            except socket.gaierror as e:
                logger.error(f"DNS FALHOU: {host} -> {e}")
                return False
            
            # Teste HTTP básico
            url = f"https://{host}"
            timeout = aiohttp.ClientTimeout(total=10, connect=5)
            
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(url) as resp:
                    logger.info(f"HTTP conectividade OK: status={resp.status}")
                    return True
                    
        except Exception as e:
            logger.error(f"Teste de conectividade falhou: {e}")
            return False

    async def abacus_describe_image(
        self,
        image_bytes: bytes,
        prompt: Optional[str] = None,
        categories: Optional[List[str]] = None,
        total_timeout_sec: int = 45,
        connect_timeout_sec: int = 15,
    ) -> Dict[str, Any]:
        """
        Chama o endpoint /describeImage do Abacus com robustez melhorada
        """
        if not self.abacus_api_key:
            raise RuntimeError("ABACUS_API_KEY não configurado")
        if not image_bytes:
            raise ValueError("image_bytes vazio")

        # Teste de conectividade primeiro
        logger.info("Testando conectividade antes da chamada...")
        connectivity_ok = await self.test_dns_connectivity()
        if not connectivity_ok:
            raise RuntimeError("Falha na conectividade com Abacus - DNS ou rede indisponível")

        url = "https://apps.abacus.ai/api/v0/describeImage"
        img_b64 = base64.b64encode(image_bytes).decode("utf-8")
        payload: Dict[str, Any] = {
            "deploymentToken": self.deployment_token,
            "deploymentId": self.deployment_id,
            "imageBase64": img_b64,
        }
        if prompt:
            payload["prompt"] = prompt
        if categories:
            payload["categories"] = categories

        headers = {
            "Authorization": f"Bearer {self.abacus_api_key}",
            "Content-Type": "application/json",
            "User-Agent": "AllegaBot/1.0",
            "Accept": "application/json"
        }

        # Configurações de timeout mais robustas
        connector = aiohttp.TCPConnector(
            limit=10,
            limit_per_host=5,
            ttl_dns_cache=300,
            use_dns_cache=True,
            keepalive_timeout=30,
            enable_cleanup_closed=True
        )
        
        timeout = aiohttp.ClientTimeout(
            total=total_timeout_sec,
            connect=connect_timeout_sec,
            sock_read=20,
            sock_connect=connect_timeout_sec
        )

        backoffs = [1.0, 2.0, 4.0]  # 3 tentativas com backoff
        last_err: Optional[Exception] = None

        logger.info(
            f"Abacus describeImage → bytes={len(image_bytes)}, b64_len={len(img_b64)}, "
            f"has_prompt={bool(prompt)}, categories={categories or 'None'}"
        )

        for attempt_idx, wait in enumerate(backoffs + [None], start=1):
            try:
                logger.info(f"Tentativa {attempt_idx} de chamada para Abacus...")
                
                async with aiohttp.ClientSession(
                    timeout=timeout, 
                    connector=connector,
                    headers={"User-Agent": "AllegaBot/1.0"}
                ) as session:
                    async with session.post(url, json=payload, headers=headers) as resp:
                        text = await resp.text()
                        logger.info(f"Resposta recebida: status={resp.status}, content_length={len(text)}")
                        
                        if resp.status == 200:
                            try:
                                data = await resp.json()
                                logger.info("✅ Abacus describeImage OK (status=200)")
                                return data
                            except Exception as e:
                                logger.warning(f"Resposta 200 mas JSON inválido: {e}; body (200 chars): {text[:200]}")
                                raise
                        elif resp.status == 503:
                            logger.warning(f"Serviço indisponível (503): {text[:300]}")
                            last_err = RuntimeError(f"Serviço Abacus indisponível: {text[:120]}")
                        elif resp.status == 401:
                            logger.error(f"Token inválido (401): {text[:300]}")
                            raise RuntimeError(f"Token de acesso inválido")
                        else:
                            logger.warning(f"Abacus describeImage falhou status={resp.status}; body (300 chars): {text[:300]}")
                            last_err = RuntimeError(f"status={resp.status} body_start={text[:120]}")
                            
            except (aiohttp.ClientConnectorError, asyncio.TimeoutError, aiohttp.ServerDisconnectedError) as e:
                logger.warning(f"Tentativa {attempt_idx} falhou (rede/timeout): {type(e).__name__}: {e}")
                last_err = e
            except Exception as e:
                logger.error(f"Tentativa {attempt_idx} falhou (erro inesperado): {type(e).__name__}: {e}")
                last_err = e

            if wait is not None:
                logger.info(f"Aguardando {wait}s antes da próxima tentativa...")
                await asyncio.sleep(wait)

        # Fechar connector
        await connector.close()
        
        raise last_err or RuntimeError("Falha ao chamar Abacus describeImage após todas as tentativas")

    async def analyze_property_image(self, image_bytes: bytes, analysis_type: str = "complete") -> dict:
        """
        Analisa a imagem de imóvel usando o deployment configurado, com retries/robustez.
        """
        try:
            logger.info(f"Analisando imagem ({len(image_bytes)} bytes), tipo: {analysis_type}")

            # Monte um prompt opcional se quiser enriquecer a análise
            prompt = None
            if analysis_type and analysis_type != "complete":
                prompt = f"Faça uma análise focalizada no tipo '{analysis_type}' para esta imagem de imóvel."

            # Categories no payload para manter semântica anterior
            categories = [analysis_type] if analysis_type else None

            result = await self.abacus_describe_image(
                image_bytes=image_bytes,
                prompt=prompt,
                categories=categories,
            )

            logger.info(f"Resultado da análise recebido com sucesso (chaves: {list(result.keys())[:6]})")
            return result

        except Exception as e:
            logger.error(f"Erro ao analisar imagem: {e}")
            return {"success": False, "error": str(e)}

    async def check_property_availability_by_image(self, image_bytes: bytes) -> dict:
        """Verifica disponibilidade específica do imóvel"""
        analysis = await self.analyze_property_image(image_bytes, analysis_type="availability")
        return {
            "is_available": analysis.get("availability_status") == "disponível",
            "confidence": analysis.get("confidence", 0),
            "reasoning": analysis.get("reasoning", "Análise não disponível"),
            "recommendation": "Entre em contato para confirmar disponibilidade"
        }

    def format_analysis_response(self, analysis_result: Dict, user_message: str) -> str:
        """Formata a resposta da análise para o usuário"""
        if not analysis_result.get("success", True):
            error_msg = analysis_result.get("error", "Erro desconhecido")
            
            # Mensagens específicas para diferentes tipos de erro
            if "DNS resolution failure" in error_msg or "conectividade" in error_msg:
                return """
🔧 *Serviço de análise temporariamente indisponível*

Nosso sistema de análise de imagens está com problemas de conectividade. 

📞 *Entre em contato direto para análise manual:*
🏠 Vendas: (41) 99214-6670
🏡 Locação: (41) 99223-0874

*Nossos especialistas analisarão sua imagem pessoalmente!*
                """
            elif "Token" in error_msg or "401" in error_msg:
                return """
🔧 *Sistema em manutenção*

Nosso sistema de análise está sendo atualizado.

📞 *Fale direto com nossos especialistas:*
🏠 Vendas: (41) 99214-6670
🏡 Locação: (41) 99223-0874

*Eles analisarão sua imagem na hora!*
                """
            else:
                return """
😅 *Tive dificuldade para analisar esta imagem.*

📸 *Dicas para melhores resultados:*
• Use fotos claras e bem iluminadas
• Evite imagens muito distantes
• Certifique-se que placas/textos estão visíveis

📞 *Ou fale direto com nossos especialistas:*
🏠 Vendas: (41) 99214-6670
🏡 Locação: (41) 99223-0874
                """

        # Resposta padrão formatada
        response = "🏠 *Análise do Imóvel Concluída*\n\n"
        
        # Adicionar informações básicas se disponíveis
        if analysis_result.get("property_type"):
            response += f"🏡 *Tipo:* {analysis_result['property_type']}\n"
        
        if analysis_result.get("description"):
            description = analysis_result["description"][:200]
            response += f"📝 *Descrição:* {description}...\n"
        
        response += "\n💡 *Análise detalhada realizada com sucesso!*\n"
        response += "\n📞 *Quer mais informações? Entre em contato:*\n"
        response += "🏠 Vendas: (41) 99214-6670\n"
        response += "🏡 Locação: (41) 99223-0874"
        
        return response

# Instância global
property_image_analyzer = PropertyImageAnalyzer(
    deployment_token="0c3a137697cb4bc8aee4415dd291fa1b",
    deployment_id="e0a6b28e0"
)

class PropertyChatbot:
    """Chatbot especializado em análise de imóveis"""
    
    def __init__(self):
        self.analyzer = property_image_analyzer
        self.conversation_history = {}
        
        # Respostas padrão do chatbot
        self.responses = {
            'greeting': """
🏠 *Olá! Sou o assistente da Allega Imóveis!*

Posso te ajudar com:
• 📸 Analisar fotos de imóveis
• 🔍 Verificar disponibilidade
• 📞 Encontrar contatos de imobiliárias
• 💰 Estimar características e valores

*Como posso ajudar você hoje?*

📞 Contatos diretos:
🏠 Vendas: (41) 99214-6670
🏡 Locação: (41) 99223-0874
            """,
            
            'help': """
🤖 *Como usar o assistente:*

📸 *Para analisar imóveis:*
• Envie uma foto do imóvel
• Eu analiso automaticamente
• Receba informações detalhadas

💬 *Comandos úteis:*
• "analisar" - para análise detalhada
• "disponibilidade" - verificar se está disponível
• "contatos" - extrair telefones da imagem
• "ajuda" - ver esta mensagem

📞 *Precisa de mais ajuda?*
🏠 Vendas: (41) 99214-6670
🏡 Locação: (41) 99223-0874
            """,
            
            'no_image': """
📸 *Preciso de uma imagem para analisar!*

Envie uma foto do imóvel que você quer analisar e eu te ajudo com:
• Tipo de imóvel
• Características principais
• Status de disponibilidade
• Contatos da imobiliária
• Recomendações

*Dica:* Use fotos claras e bem iluminadas para melhores resultados!
            """
        }
    
    async def process_message(self, user_id: str, message: str, image_data: bytes = None) -> str:
        """Processa mensagem do usuário (texto + imagem opcional)"""
        try:
            # Salvar histórico
            if user_id not in self.conversation_history:
                self.conversation_history[user_id] = []
            
            self.conversation_history[user_id].append({
                'timestamp': datetime.now().isoformat(),
                'message': message,
                'has_image': bool(image_data)
            })
            
            # Processar mensagem
            message_lower = message.lower().strip()
            
            # Comandos especiais
            if any(word in message_lower for word in ['oi', 'olá', 'hello', 'início', 'start']):
                return self.responses['greeting']
            
            elif any(word in message_lower for word in ['ajuda', 'help', 'comandos']):
                return self.responses['help']
            
            # Se tem imagem, processar análise
            elif image_data:
                return await self._process_image_analysis(user_id, message, image_data)
            
            # Se não tem imagem mas pede análise
            elif any(word in message_lower for word in ['analisar', 'análise', 'foto', 'imagem']):
                return self.responses['no_image']
            
            # Resposta padrão para texto sem imagem
            else:
                return await self._process_text_only(message)
                
        except Exception as e:
            logger.error(f"Erro processando mensagem: {str(e)}")
            return self._get_error_response()
    
    async def _process_image_analysis(self, user_id: str, message: str, image_data: bytes) -> str:
        """Processa análise de imagem"""
        try:
            # Determinar tipo de análise baseado na mensagem
            analysis_type = self._determine_analysis_type(message)
            
            # Executar análise
            logger.info(f"Iniciando análise de imagem para usuário {user_id} - Tipo: {analysis_type}")
            analysis_result = await self.analyzer.analyze_property_image(image_data, analysis_type)
            
            # Salvar resultado no histórico
            self.conversation_history[user_id].append({
                'timestamp': datetime.now().isoformat(),
                'analysis_result': analysis_result.get('metadata', {}),
                'analysis_type': analysis_type
            })
            
            # Formatar resposta baseada no tipo de análise
            if analysis_type == "availability":
                return await self._format_availability_response(analysis_result, image_data)
            elif analysis_type == "contact":
                return await self._format_contact_response(analysis_result)
            else:
                return self.analyzer.format_analysis_response(analysis_result, message)
                
        except Exception as e:
            logger.error(f"Erro na análise de imagem: {str(e)}")
            return self._get_analysis_error_response()
    
    def _determine_analysis_type(self, message: str) -> str:
        """Determina o tipo de análise baseado na mensagem do usuário"""
        message_lower = message.lower()
        
        if any(word in message_lower for word in ['disponível', 'disponibilidade', 'livre', 'ocupado', 'vago']):
            return "availability"
        elif any(word in message_lower for word in ['contato', 'telefone', 'whatsapp', 'imobiliária']):
            return "contact"
        else:
            return "complete"
    
    async def _format_availability_response(self, analysis: Dict, image_data: bytes) -> str:
        """Formata resposta específica para disponibilidade"""
        try:
            if not analysis.get('success', True):
                return "😅 Não consegui determinar a disponibilidade desta imagem. Tente com uma foto mais clara!"
            
            # Usar o método específico do analyzer
            availability_check = await self.analyzer.check_property_availability_by_image(image_data)
            
            response = "🔍 *Verificação de Disponibilidade*\n\n"
            
            if availability_check['is_available'] is True:
                response += "✅ *APARENTA ESTAR DISPONÍVEL*\n"
            elif availability_check['is_available'] is False:
                response += "❌ *APARENTA ESTAR INDISPONÍVEL*\n"
            else:
                response += "❓ *STATUS INCERTO*\n"
            
            response += f"\n💡 *Análise:* {availability_check['reasoning'][:100]}...\n"
            response += f"🎯 *Confiança:* {availability_check['confidence']}/10\n"
            response += f"\n📋 *Recomendação:* {availability_check['recommendation']}\n"
            
            # Adicionar contatos padrão
            response += "\n📞 *Quer confirmar? Entre em contato:*\n"
            response += "🏠 Vendas: (41) 99214-6670\n"
            response += "🏡 Locação: (41) 99223-0874"
            
            return response
            
        except Exception as e:
            logger.error(f"Erro formatando resposta de disponibilidade: {str(e)}")
            return self._get_analysis_error_response()
    
    async def _format_contact_response(self, analysis: Dict) -> str:
        """Formata resposta específica para contatos"""
        try:
            response = "📞 *Contatos Encontrados na Imagem*\n\n"
            
            contact_info = analysis.get('contact_info', {})
            found_any = False
            
            # Telefones
            if contact_info.get('phones'):
                response += "📱 *Telefones:*\n"
                for phone in contact_info['phones'][:3]:  # Máximo 3
                    response += f"• {phone}\n"
                found_any = True
            
            # Empresas/Imobiliárias
            if contact_info.get('companies'):
                response += "\n🏢 *Imobiliárias:*\n"
                companies = set(contact_info['companies'])
                for company in list(companies)[:3]:
                    response += f"• {company.title()}\n"
                found_any = True
            
            # Emails
            if contact_info.get('emails'):
                response += "\n📧 *Emails:*\n"
                for email in contact_info['emails'][:2]:
                    response += f"• {email}\n"
                found_any = True
            
            # Sites
            if contact_info.get('websites'):
                response += "\n🌐 *Sites:*\n"
                for site in contact_info['websites'][:2]:
                    response += f"• {site}\n"
                found_any = True
            
            if not found_any:
                response = "😅 *Não encontrei contatos visíveis nesta imagem.*\n\n"
                response += "💡 *Dicas:*\n"
                response += "• Certifique-se que há placas ou anúncios visíveis\n"
                response += "• Use uma foto mais próxima dos textos\n"
                response += "• Verifique se a imagem está nítida\n\n"
            
            # Sempre adicionar contatos da Allega
            response += "\n📞 *Nossos contatos para ajudar:*\n"
            response += "🏠 Vendas: (41) 99214-6670\n"
            response += "🏡 Locação: (41) 99223-0874"
            
            return response
            
        except Exception as e:
            logger.error(f"Erro formatando resposta de contatos: {str(e)}")
            return self._get_analysis_error_response()
    
    async def _process_text_only(self, message: str) -> str:
        """Processa mensagens apenas de texto"""
        message_lower = message.lower()
        
        # Perguntas sobre serviços
        if any(word in message_lower for word in ['preço', 'valor', 'quanto custa']):
            return """
💰 *Consulta de Preços*

Para te dar informações precisas sobre preços, preciso saber:
• Que tipo de imóvel você procura?
• Em qual região/bairro?
• Quantos quartos?

📸 *Ou envie uma foto* do imóvel que te interessou!

📞 *Fale direto com nossos especialistas:*
🏠 Vendas: (41) 99214-6670
🏡 Locação: (41) 99223-0874
            """
        
        elif any(word in message_lower for word in ['visita', 'agendar', 'ver imóvel']):
            return """
📅 *Agendamento de Visitas*

Quer agendar uma visita? É só entrar em contato:

📞 *Nossos especialistas:*
🏠 Vendas: (41) 99214-6670
🏡 Locação: (41) 99223-0874

💡 *Dica:* Envie uma foto do imóvel que te interessou para eu te dar mais informações antes da visita!
            """
        
        elif any(word in message_lower for word in ['obrigado', 'obrigada', 'valeu', 'thanks']):
            return """
😊 *Por nada! Foi um prazer ajudar!*

Sempre que precisar de análise de imóveis, estarei aqui!

📞 *Nossos contatos:*
🏠 Vendas: (41) 99214-6670
🏡 Locação: (41) 99223-0874

*Até a próxima!* 🏠✨
            """
        
        # Resposta padrão
        else:
            return """
🤖 *Não entendi bem sua mensagem.*

Posso te ajudar com:
• 📸 Analisar fotos de imóveis
• 🔍 Verificar disponibilidade
• 📞 Encontrar contatos
• 💰 Informações sobre preços

*Envie uma foto de um imóvel ou digite "ajuda" para ver todos os comandos.*

📞 *Ou fale direto conosco:*
🏠 Vendas: (41) 99214-6670
🏡 Locação: (41) 99223-0874
            """
    
    def _get_error_response(self) -> str:
        """Resposta padrão para erros"""
        return """
😅 *Ops! Algo deu errado.*

Tente novamente ou entre em contato diretamente:

📞 *Nossos especialistas:*
🏠 Vendas: (41) 99214-6670
🏡 Locação: (41) 99223-0874

*Estamos aqui para ajudar!* 🏠
        """
    
    def _get_analysis_error_response(self) -> str:
        """Resposta específica para erros de análise"""
        return """
🔧 *Sistema de análise temporariamente indisponível*

📞 *Nossos especialistas analisarão sua imagem pessoalmente:*
🏠 Vendas: (41) 99214-6670
🏡 Locação: (41) 99223-0874

*Envie a imagem diretamente para eles via WhatsApp!*
        """
    
    def get_user_stats(self, user_id: str) -> Dict:
        """Retorna estatísticas do usuário"""
        if user_id not in self.conversation_history:
            return {'messages': 0, 'images_analyzed': 0}
        
        history = self.conversation_history[user_id]
        return {
            'messages': len(history),
            'images_analyzed': sum(1 for msg in history if msg.get('has_image')),
            'last_interaction': history[-1]['timestamp'] if history else None
        }

# Instância global do chatbot
property_chatbot = PropertyChatbot()