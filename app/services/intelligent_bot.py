"""
Integração Principal do Sistema de Inteligência Imobiliária
Coordena IA, extração de dados e resposta inteligente com análise de imagens
"""

import asyncio
import logging
from typing import Dict, Any, Optional
from datetime import datetime
import aiohttp
import base64
import os

logger = logging.getLogger("IntelligentRealEstateBot")
logger.setLevel(logging.INFO)
if not logger.hasHandlers():
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)

class IntelligentRealEstateBot:
    """Bot inteligente especializado em imóveis usando Groq"""

    def __init__(self):
        self.groq_api_key = os.getenv("GROQ_API_KEY")
        self.text_model = "llama3-8b-8192"
        self.vision_model = "llama-3.2-11b-vision-preview"
        self.bot_config = {
            'company_name': 'Allega Imóveis',
            'response_style': 'friendly_professional',
            'enable_property_search': True,
            'enable_market_insights': True,
            'enable_image_analysis': True,
            'max_properties_per_response': 3
        }
        logger.info("Bot de Inteligência Imobiliária com Groq iniciado")

    async def process_message(self, message: str, user_phone: str) -> str:
        """Processa mensagem do usuário com Groq"""
        try:
            logger.info(f"📨 Mensagem de {user_phone}: {message[:50]}...")

            # Verificar se é busca de imóveis
            if self._is_property_search(message):
                property_response = await self.process_property_search(message)
                if property_response and "não está disponível" not in property_response:
                    return property_response
            
            prompt = self._build_prompt(message, user_phone)
            response = await self._call_groq(prompt)
            logger.info(f"✅ Resposta enviada para {user_phone}")
            return response
        except Exception as e:
            logger.error(f"❌ Erro ao processar mensagem: {str(e)}")
            return (
                "😅 Ops! Tive um probleminha técnico, mas já estou me recuperando!\n\n"
                "Enquanto isso, você pode entrar em contato diretamente:\n"
                "📞 Vendas: (41) 99214-6670\n"
                "📞 Locação: (41) 99223-0874\n\n"
                "Nossos especialistas estão prontos para ajudar! 😊"
            )

    async def process_image_message(self, image_data: bytes, caption: str, user_phone: str) -> str:
        """Processa imagem enviada pelo usuário usando Groq Vision"""
        try:
            logger.info(f"📸 Imagem recebida de {user_phone} - Tamanho: {len(image_data)} bytes")
            
            # Converter imagem para base64
            image_b64 = base64.b64encode(image_data).decode("utf-8")
            
            # Criar prompt para análise de imagem
            prompt = self._build_image_prompt(caption, user_phone)
            
            # Chamar Groq Vision
            response = await self._call_groq_vision(prompt, image_b64)
            
            logger.info(f"✅ Análise de imagem concluída para {user_phone}")
            return response
            
        except Exception as e:
            logger.error(f"❌ Erro ao processar imagem: {str(e)}")
            return (
                "📸 Recebi sua imagem!\n\n"
                "😅 Tive dificuldade técnica para analisá-la no momento.\n\n"
                "🏠 *Mas posso ajudar de outras formas:*\n"
                "• Descreva o imóvel que procura\n"
                "• Informe sua localização preferida\n"
                "• Conte sobre seu orçamento\n\n"
                "📞 *Ou entre em contato direto:*\n"
                "🏠 Vendas: (41) 99214-6670\n"
                "🏡 Locação: (41) 99223-0874"
            )

    def _build_prompt(self, message: str, user_phone: str) -> str:
        """Constrói o prompt para o Groq"""
        return (
            f"Você é a Sofia, assistente virtual para a imobiliária Allega Imóveis, que atende clientes via WhatsApp, fornecendo informações detalhadas e precisas sobre imóveis disponíveis exclusivamente na região de Curitiba e região metropolitana. Seu principal objetivo é ajudar leads a:\n\n"
            f"- Consultar imóveis disponíveis para venda ou aluguel\n"
            f"- Responder dúvidas sobre características dos imóveis (quantidade de quartos, localização, diferenciais como proximidade a mercado, transporte, segurança)\n"
            f"- Ajudar a agendar visitas com corretores quando solicitado\n"
            f"- Analisar mensagens de texto e imagens (prints de anúncios de imóveis de plataformas externas, fotos de fachadas etc.) enviada pelo cliente para verificar disponibilidade e detalhes do imóvel no banco de dados atualizado da imobiliária\n\n"
            f"Regras e funcionalidades obrigatórias:\n\n"
            f"Base de Conhecimento: Você só pode responder com as informações que constam no banco de dados da imobiliária Allega Imóveis, que contém os dados atualizados do site oficial (https://www.allegaimoveis.com).\n\n"
            f"Respostas contextuais: Em caso de dúvidas específicas (quartos, valor, localização), responda com base nos dados indexados.\n\n"
            f"Interpretação de Imagens (modelo multimodal): Quando o cliente enviar uma imagem (print ou foto), analise o conteúdo visual, identifique o imóvel através de elementos visuais e texto embutido na imagem, e faça cruzamento com a base de dados para confirmar disponibilidade e características do imóvel.\n\n"
            f"Se o imóvel estiver disponível, responda com todos os detalhes relevantes e ofereça marcar uma visita com corretor.\n\n"
            f"Se o imóvel não estiver disponível ou não for encontrado, informe isso de forma clara e sugira outros imóveis semelhante ao que o cliente procura.\n\n"
            f"Atualização Dinâmica: Esteja preparado para consultar os dados mais recentes da base, que são continuamente atualizados automaticamente. Nunca invente informações ou responda fora do escopo autorizado.\n\n"
            f"Tom e linguagem: Use linguagem formal, humana, clara, cordial e profissional, adequada para atendimento ao cliente no setor imobiliário.\n\n"
            f"INFORMAÇÕES DA IMOBILIÁRIA:\n"
            f"- Nome: Allega Imóveis\n"
            f"- Telefones: (41) 3285-1383, (41) 99214-6670, (41) 99223-0874\n"
            f"- CRECI: 6684 J\n"
            f"- Email: contato@allegaimoveis.com\n"
            f"- Endereço: Rua Gastão Câmara, 135 - Bigorrilho, Curitiba - PR\n\n"
            f"REGRAS OBRIGATÓRIAS:\n"
            f"1. Só responda sobre imóveis que estão na base de dados.\n"
            f"2. Seja cordial, profissional e objetivo\n"
            f"3. Sempre ofereça agendamento de visitas quando apropriado\n"
            f"4. Para imagens enviadas, descreva o que vê e verifique se temos imóvel similar\n"
            f"5. Quando não tiver informações específicas sobre um imóvel consultado, responda: 'No momento não tenho essa informação específica em nossa base. Posso conectá-lo com um de nossos corretores para mais detalhes?'\n\n"
            f"EXEMPLOS DE RESPOSTAS:\n"
            f"- Para 'Tem casas no Bigorrilho?': 'Sim, temos várias opções no Bigorrilho! Gostaria de saber sobre casas para venda ou aluguel? Posso agendar uma visita com nossos corretores.'\n"
            f"- Para análise de imagem: 'Analisei a imagem que você enviou. Vi que é um apartamento de 2 quartos. Deixe-me verificar se temos opções similares disponíveis em nosso portfólio...'\n"
            f"- Para agendamento: 'Fico feliz em saber do seu interesse! Posso agendar uma visita com um dos nossos corretores. Qual seria o melhor dia e horário para você?' e sugira três horários nos próximos dias de acordo com agenda do corretor.\n\n"
            f"Usuário ({user_phone}) enviou: \"{message}\"\n\n"
            f"Responda como Sofia, seguindo todas as regras acima."
        )

    def _build_image_prompt(self, caption: str, user_phone: str) -> str:
        """Constrói prompt específico para análise de imagens"""
        return (
            f"Você é a Sofia, assistente virtual da Allega Imóveis. Analise esta imagem de imóvel enviada pelo cliente.\n\n"
            f"INSTRUÇÕES PARA ANÁLISE:\n"
            f"1. Descreva detalhadamente o que você vê na imagem\n"
            f"2. Identifique características do imóvel (tipo, quartos, área, localização se visível)\n"
            f"3. Se for um print de anúncio, extraia todas as informações disponíveis\n"
            f"4. Verifique se temos imóveis similares em nossa base\n"
            f"5. Seja cordial e ofereça ajuda adicional\n\n"
            f"Mensagem do usuário: {caption}\n\n"
            f"Responda como Sofia da Allega Imóveis, sendo profissional e prestativa."
        )

    async def _call_groq(self, prompt: str) -> str:
        """Chama API do Groq para texto"""
        if not self.groq_api_key:
            return "Configuração da API não encontrada."
        
        payload = {
            "model": self.text_model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 1000,
            "temperature": 0.7
        }
        
        headers = {
            "Authorization": f"Bearer {self.groq_api_key}",
            "Content-Type": "application/json"
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post("https://api.groq.com/openai/v1/chat/completions", 
                                    json=payload, headers=headers, 
                                    timeout=aiohttp.ClientTimeout(total=30)) as resp:
                    if resp.status == 200:
                        result = await resp.json()
                        return result["choices"][0]["message"]["content"]
                    else:
                        error_text = await resp.text()
                        logger.error(f"Erro Groq: {resp.status} - {error_text}")
                        return "😅 Tive dificuldade técnica para responder no momento."
        except Exception as e:
            logger.error(f"Erro ao chamar Groq: {str(e)}")
            return "😅 Tive dificuldade técnica para responder no momento."

    async def _call_groq_vision(self, prompt: str, image_b64: str) -> str:
        """Chama API do Groq para análise de imagem"""
        if not self.groq_api_key:
            return "Configuração da API não encontrada."
        
        payload = {
            "model": self.vision_model,
            "messages": [{
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{image_b64}"
                        }
                    }
                ]
            }],
            "max_tokens": 1000,
            "temperature": 0.7
        }
        
        headers = {
            "Authorization": f"Bearer {self.groq_api_key}",
            "Content-Type": "application/json"
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post("https://api.groq.com/openai/v1/chat/completions", 
                                    json=payload, headers=headers, 
                                    timeout=aiohttp.ClientTimeout(total=60)) as resp:
                    if resp.status == 200:
                        result = await resp.json()
                        content = result["choices"][0]["message"]["content"]
                        return f"🏠 *Análise do Imóvel Concluída*\n\n{content}\n\n💡 *Posso ajudar com mais alguma coisa?*"
                    else:
                        error_text = await resp.text()
                        logger.error(f"Erro Groq Vision: {resp.status} - {error_text}")
                        return (
                            "📸 Recebi sua imagem!\n\n"
                            "😅 Tive dificuldade técnica para analisá-la no momento.\n\n"
                            "🏠 *Mas posso ajudar de outras formas:*\n"
                            "• Descreva o imóvel que procura\n"
                            "• Informe sua localização preferida\n"
                            "• Conte sobre seu orçamento\n\n"
                            "📞 *Ou entre em contato direto:*\n"
                            "🏠 Vendas: (41) 99214-6670\n"
                            "🏡 Locação: (41) 99223-0874"
                        )
        except Exception as e:
            logger.error(f"Erro ao chamar Groq Vision: {str(e)}")
            return (
                "📸 Recebi sua imagem!\n\n"
                "😅 Tive dificuldade técnica para analisá-la no momento.\n\n"
                "🏠 *Mas posso ajudar de outras formas:*\n"
                "• Descreva o imóvel que procura\n"
                "• Informe sua localização preferida\n"
                "• Conte sobre seu orçamento\n\n"
                "📞 *Ou entre em contato direto:*\n"
                "🏠 Vendas: (41) 99214-6670\n"
                "🏡 Locação: (41) 99223-0874"
            )

    def _is_property_search(self, message: str) -> bool:
        """Verifica se a mensagem é uma busca por imóveis"""
        keywords = [
            "casa", "apartamento", "imóvel", "quartos", "bairro", "comprar", 
            "alugar", "locação", "venda", "preço", "valor", "m²", "garagem",
            "sala", "cozinha", "banheiro", "área", "terreno", "condomínio",
            "studio", "kitnet", "cobertura", "sobrado", "comercial"
        ]
        return any(kw in message.lower() for kw in keywords)

# Instância global do bot
intelligent_bot = IntelligentRealEstateBot()