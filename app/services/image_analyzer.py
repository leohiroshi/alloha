"""
Chatbot Inteligente para Análise de Imóveis
Integra o PropertyImageAnalyzer com interface de chat
"""

import asyncio
import logging
from typing import Dict, Any, Optional
from datetime import datetime
import json
from abacusai import ApiClient
from property_image_analyzer import property_image_analyzer

# Configuração de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PropertyImageAnalyzer:
    def __init__(self, deployment_token: str, deployment_id: str):
        self.client = ApiClient()
        self.deployment_token = deployment_token
        self.deployment_id = deployment_id

    async def analyze_property_image(self, image_bytes: bytes, analysis_type: str = "complete") -> dict:
        # Converte a imagem para base64
        import base64
        image_b64 = base64.b64encode(image_bytes).decode("utf-8")
        # Chama o endpoint de descrição de imagem do Abacus
        result = self.client.describe_image(
            deployment_token=self.deployment_token,
            deployment_id=self.deployment_id,
            image_base64=image_b64
        )
        return result

# Exemplo de instância global
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
                return await self._format_availability_response(analysis_result)
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
    
    async def _format_availability_response(self, analysis: Dict) -> str:
        """Formata resposta específica para disponibilidade"""
        try:
            if not analysis.get('success'):
                return "😅 Não consegui determinar a disponibilidade desta imagem. Tente com uma foto mais clara!"
            
            # Usar o método específico do analyzer
            availability_check = await self.analyzer.check_property_availability_by_image(b'')  # Já foi analisada
            
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
😅 *Tive dificuldade para analisar esta imagem.*

📸 *Dicas para melhores resultados:*
• Use fotos claras e bem iluminadas
• Evite imagens muito distantes
• Certifique-se que placas/textos estão visíveis

📞 *Ou fale direto com nossos especialistas:*
🏠 Vendas: (41) 99214-6670
🏡 Locação: (41) 99223-0874
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