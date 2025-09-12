"""
Integração Principal do Sistema de Inteligência Imobiliária
Coordena IA, extração de dados e resposta inteligente com análise de imagens
"""

import asyncio
import logging
from typing import Dict, Any, Optional
from datetime import datetime

from .ai_service import AIService
from .firebase_service import FirebaseService
from .property_intelligence import PropertyIntelligenceService
from .image_analyzer import PropertyImageAnalyzer
from app.services.firebase_service import firebase_service


logger = logging.getLogger("IntelligentRealEstateBot")
logger.setLevel(logging.INFO)
if not logger.hasHandlers():
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)

class IntelligentRealEstateBot:
    """Bot inteligente especializado em imóveis com análise de imagens"""
    
    def __init__(self):
        self.firebase_service = firebase_service 
        self.image_analyzer = PropertyImageAnalyzer(
            deployment_token="0c3a137697cb4bc8aee4415dd291fa1b",
            deployment_id="e0a6b28e0"
        )
        
        # Configurações do bot
        self.bot_config = {
            'company_name': 'Allega Imóveis',
            'response_style': 'friendly_professional',
            'enable_property_search': True,
            'enable_market_insights': True,
            'enable_image_analysis': True,
            'max_properties_per_response': 3
        }
        
        logger.info("🤖 Bot de Inteligência Imobiliária com Análise de Imagens iniciado")
    
    async def process_message(self, message: str, user_phone: str) -> str:
        """Processa mensagem do usuário com inteligência completa"""
        try:
            # Log da mensagem recebida
            logger.info(f"📨 Mensagem de {user_phone}: {message[:50]}...")
            
            # Salvar mensagem no Firebase
            await self.firebase_service.save_message(
                user_phone=user_phone,
                message=message,
                direction="received"
            )
            
            # Verificar se é relacionado a imóveis
            if self.property_intelligence.is_property_related(message):
                logger.info("🏠 Mensagem identificada como relacionada a imóveis")
                
                # Processar com inteligência imobiliária
                response = await self.property_intelligence.process_property_inquiry(
                    message=message,
                    user_id=user_phone
                )
            else:
                # Processar com IA geral
                logger.info("💬 Processando com IA geral")
                response = await self.ai_service.generate_response(
                    message=message,
                    user_phone=user_phone
                )
            
            # Salvar resposta no Firebase
            await self.firebase_service.save_message(
                user_phone=user_phone,
                message=response,
                direction="sent"
            )
            
            logger.info(f"✅ Resposta enviada para {user_phone}")
            return response
            
        except Exception as e:
            logger.error(f"❌ Erro ao processar mensagem: {str(e)}")
            
            # Resposta de fallback
            fallback_response = (
                "😅 Ops! Tive um probleminha técnico, mas já estou me recuperando!\n\n"
                "Enquanto isso, você pode entrar em contato diretamente:\n"
                "📞 Vendas: (41) 99214-6670\n"
                "📞 Locação: (41) 99223-0874\n\n"
                "Nossos especialistas estão prontos para ajudar! 😊"
            )
            
            # Tentar salvar erro no Firebase
            try:
                await self.firebase_service.save_message(
                    user_phone=user_phone,
                    message=fallback_response,
                    direction="sent"
                )
            except:
                pass
            
            return fallback_response
    
    async def process_image_message(self, image_data: bytes, caption: str, user_phone: str) -> str:
        """Processa imagem enviada pelo usuário"""
        try:
            logger.info(f"📸 Imagem recebida de {user_phone} - Tamanho: {len(image_data)} bytes")
            
            # Salvar informação da imagem no Firebase
            await self.firebase_service.save_message(
                user_phone=user_phone,
                message=f"[IMAGEM] {caption}" if caption else "[IMAGEM]",
                direction="received"
            )
            
            # Analisar imagem
            analysis_result = await self.image_analyzer.analyze_property_image(
                image_bytes=image_data,
                analysis_type="complete"
            )
            
            # Verificar se foi bem-sucedida
            if not analysis_result.get('success'):
                response = (
                    "📸 Recebi sua imagem!\n\n"
                    "😅 Tive um pouco de dificuldade para analisá-la, mas posso ajudar de outras formas:\n\n"
                    "🏠 *Posso ajudar com:*\n"
                    "• Buscar imóveis similares\n"
                    "• Informações sobre preços\n"
                    "• Verificar disponibilidade\n"
                    "• Agendar visitas\n\n"
                    "📞 *Contatos diretos:*\n"
                    "🏠 Vendas: (41) 99214-6670\n"
                    "🏡 Locação: (41) 99223-0874\n\n"
                    "💡 *Dica:* Descreva o imóvel que procura!"
                )
            else:
                # Gerar resposta baseada na análise
                response = self.image_analyzer.format_analysis_response(
                    analysis_result, 
                    caption
                )
                
                # Adicionar sugestões baseadas na análise
                response += self._generate_image_suggestions(analysis_result, user_phone)
            
            # Salvar resposta no Firebase
            await self.firebase_service.save_message(
                user_phone=user_phone,
                message=response,
                direction="sent"
            )
            
            # Salvar análise da imagem para analytics
            await self._save_image_analysis(user_phone, analysis_result, caption)
            
            logger.info(f"✅ Análise de imagem concluída para {user_phone}")
            return response
            
        except Exception as e:
            logger.error(f"❌ Erro ao processar imagem: {str(e)}")
            
            fallback_response = (
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
            
            try:
                await self.firebase_service.save_message(
                    user_phone=user_phone,
                    message=fallback_response,
                    direction="sent"
                )
            except:
                pass
            
            return fallback_response
    
    def _generate_image_suggestions(self, analysis: Dict[str, Any], user_phone: str) -> str:
        """Gera sugestões baseadas na análise da imagem"""
        try:
            suggestions = "\n\n🎯 *Posso ajudar você com:*\n"
            
            # Sugestões baseadas no tipo de imóvel
            property_type = analysis.get('property_type', '').lower()
            if 'apartamento' in property_type:
                suggestions += "• Buscar apartamentos similares\n"
                suggestions += "• Informar preços de apartamentos na região\n"
            elif 'casa' in property_type:
                suggestions += "• Buscar casas similares\n"
                suggestions += "• Comparar preços de casas\n"
            else:
                suggestions += "• Buscar imóveis similares\n"
                suggestions += "• Informações sobre o mercado\n"
            
            # Sugestões baseadas na disponibilidade
            availability = analysis.get('availability_status', '').lower()
            if 'disponível' in availability:
                suggestions += "• Agendar visita para este imóvel\n"
                suggestions += "• Informações sobre financiamento\n"
            elif 'indisponível' in availability:
                suggestions += "• Buscar alternativas disponíveis\n"
                suggestions += "• Cadastrar alerta para imóveis similares\n"
            else:
                suggestions += "• Verificar status atualizado\n"
                suggestions += "• Buscar opções disponíveis\n"
            
            # Contatos encontrados na imagem
            contact_info = analysis.get('contact_info', {})
            if contact_info.get('phones'):
                suggestions += "\n📱 *Contatos identificados na imagem:*\n"
                for phone in contact_info['phones'][:2]:
                    suggestions += f"• {phone}\n"
                suggestions += "\n💡 *Posso ajudar a conectar você!*"
            
            return suggestions
            
        except Exception as e:
            logger.error(f"Erro gerando sugestões: {str(e)}")
            return "\n\n💬 Como posso ajudar você hoje?"
    
    async def _save_image_analysis(self, user_phone: str, analysis: Dict, caption: str):
        """Salva análise da imagem para analytics"""
        try:
            analysis_data = {
                'user_phone': user_phone,
                'timestamp': datetime.now(),
                'analysis_result': analysis,
                'caption': caption,
                'success': analysis.get('success', False),
                'property_type': analysis.get('property_type', 'unknown'),
                'availability_status': analysis.get('availability_status', 'uncertain'),
                'confidence': analysis.get('confidence', 0),
                'type': 'image_analysis'
            }
            
            # Salvar no Firebase
            await self.firebase_service.save_analytics('image_analysis', analysis_data)
            
        except Exception as e:
            logger.error(f"Erro salvando análise de imagem: {str(e)}")
    
    async def check_property_availability_from_image(self, image_data: bytes, user_phone: str) -> str:
        """Verifica especificamente a disponibilidade de um imóvel através da imagem"""
        try:
            logger.info(f"🔍 Verificando disponibilidade via imagem para {user_phone}")
            
            # Análise focada em disponibilidade
            availability_result = await self.image_analyzer.check_property_availability_by_image(image_data)
            
            # Gerar resposta específica sobre disponibilidade
            response = "🔍 *Verificação de Disponibilidade*\n\n"
            
            if availability_result['is_available'] is True:
                response += "✅ *Status:* Imóvel APARENTA estar DISPONÍVEL\n"
                response += f"🎯 *Confiança:* {availability_result['confidence']}/10\n\n"
                response += "🏠 *Próximos passos recomendados:*\n"
                response += "• Entrar em contato rapidamente\n"
                response += "• Agendar visita\n"
                response += "• Verificar documentação\n"
                
            elif availability_result['is_available'] is False:
                response += "❌ *Status:* Imóvel APARENTA estar INDISPONÍVEL\n"
                response += f"🎯 *Confiança:* {availability_result['confidence']}/10\n\n"
                response += "🔄 *Posso ajudar com:*\n"
                response += "• Buscar imóveis similares disponíveis\n"
                response += "• Cadastrar alerta para quando houver disponibilidade\n"
                response += "• Sugerir alternativas na mesma região\n"
                
            else:
                response += "❓ *Status:* NÃO FOI POSSÍVEL determinar\n"
                response += f"🎯 *Confiança:* {availability_result['confidence']}/10\n\n"
                response += "💡 *Recomendação:*\n"
                response += "• Verificar diretamente com a imobiliária\n"
                response += "• Buscar informações atualizadas online\n"
                response += "• Consultar outros canais\n"
            
            # Adicionar reasoning se disponível
            if availability_result.get('reasoning'):
                response += f"\n📝 *Análise:* {availability_result['reasoning'][:100]}...\n"
            
            # Contatos da Allega
            response += "\n📞 *Contatos Allega Imóveis:*\n"
            response += "🏠 Vendas: (41) 99214-6670\n"
            response += "🏡 Locação: (41) 99223-0874\n"
            response += "📧 contato@allegaimoveis.com"
            
            return response
            
        except Exception as e:
            logger.error(f"Erro verificando disponibilidade: {str(e)}")
            return (
                "🔍 Recebi sua solicitação de verificação!\n\n"
                "😅 Tive dificuldade técnica no momento.\n\n"
                "📞 *Verificação direta:*\n"
                "🏠 Vendas: (41) 99214-6670\n"
                "🏡 Locação: (41) 99223-0874\n\n"
                "💬 Ou descreva o imóvel que procura!"
            )
    
    async def handle_special_commands(self, message: str, user_phone: str) -> Optional[str]:
        """Processa comandos especiais do sistema"""
        message_lower = message.lower().strip()
        
        # Comando para insights de mercado
        if message_lower in ['mercado', 'insights', 'estatísticas', 'dados']:
            return self.property_intelligence.get_market_insights()
        
        # Comando para informações da empresa
        elif message_lower in ['empresa', 'contato', 'info', 'informações']:
            return self._get_company_info()
        
        # Comando para ajuda
        elif message_lower in ['ajuda', 'help', 'menu', 'comandos']:
            return self._get_help_menu()
        
        # Comando para status do sistema
        elif message_lower in ['status', 'sistema']:
            return await self._get_system_status()
        
        return None
    
    def _get_company_info(self) -> str:
        """Retorna informações da empresa"""
        return (
            "🏢 *Allega Imóveis - CRECI 6684 J*\n\n"
            "📍 *Endereço:*\n"
            "Rua Gastão Câmara, 135 - Bigorrilho\n"
            "Curitiba - PR\n\n"
            "📞 *Contatos:*\n"
            "• Vendas: (41) 99214-6670\n"
            "• Locação: (41) 99223-0874\n"
            "• Fixo: (41) 3285-1383\n"
            "• Email: contato@allegaimoveis.com\n\n"
            "🌐 *Website:*\n"
            "https://www.allegaimoveis.com\n\n"
            "💼 *Serviços:*\n"
            "• Venda de imóveis\n"
            "• Locação residencial e comercial\n"
            "• Lançamentos imobiliários\n"
            "• Assessoria em investimentos\n\n"
            "_Profissionais certificados pelo CRECI_"
        )
    
    def _get_help_menu(self) -> str:
        """Retorna menu de ajuda"""
        return (
            "🤖 *Como posso ajudar você:*\n\n"
            "🏠 *Buscar Imóveis:*\n"
            "• \"Quero um apartamento 3 quartos\"\n"
            "• \"Casa para alugar no Centro\"\n"
            "• \"Imóveis até R$ 500 mil\"\n\n"
            "💰 *Informações de Preços:*\n"
            "• \"Quanto custa um apartamento?\"\n"
            "• \"Preços no Bigorrilho\"\n\n"
            "📅 *Agendar Visitas:*\n"
            "• \"Quero visitar um imóvel\"\n"
            "• \"Agendar visita\"\n\n"
            "📊 *Dados de Mercado:*\n"
            "• Digite: 'mercado' ou 'insights'\n\n"
            "ℹ️ *Informações da Empresa:*\n"
            "• Digite: 'empresa' ou 'contato'\n\n"
            "_Fale naturalmente! Entendo português brasileiro_ 😊"
        )
    
    async def _get_system_status(self) -> str:
        """Retorna status do sistema"""
        try:
            # Verificar conectividade do Firebase
            firebase_status = "🟢 Online"
            try:
                await self.firebase_service.check_connection()
            except:
                firebase_status = "🔴 Offline"
            
            # Verificar dados de imóveis
            property_data_status = "🟢 Carregados"
            try:
                await self.property_intelligence.load_property_data()
                if not self.property_intelligence.property_cache:
                    property_data_status = "🟡 Cache vazio"
            except:
                property_data_status = "🔴 Erro ao carregar"
            
            # Verificar IA
            ai_status = "🟢 Operacional"
            if not self.ai_service.api_key:
                ai_status = "🟡 Sem API key"
            
            return (
                "🔧 *Status do Sistema:*\n\n"
                f"🔗 Firebase: {firebase_status}\n"
                f"🏠 Dados Imóveis: {property_data_status}\n"
                f"🤖 IA: {ai_status}\n"
                f"⏰ Última atualização: {datetime.now().strftime('%H:%M:%S')}\n\n"
                "_Sistema funcionando normalmente_ ✅"
            )
            
        except Exception as e:
            logger.error(f"Erro ao verificar status: {str(e)}")
            return "⚠️ Erro ao verificar status do sistema"
    
    async def update_property_database(self) -> bool:
        """Atualiza base de dados de imóveis"""
        try:
            logger.info("🔄 Iniciando atualização da base de imóveis...")
            
            # Importar e executar scraper
            from .property_scraper import scrape_allega_properties
            
            # Extrair dados
            result = await scrape_allega_properties(max_properties=100)
            
            if result and 'knowledge_base' in result:
                # Salvar no Firebase
                success = await self.property_intelligence.update_property_data(
                    result['knowledge_base']
                )
                
                if success:
                    logger.info("✅ Base de dados de imóveis atualizada com sucesso")
                    return True
                else:
                    logger.error("❌ Erro ao salvar dados no Firebase")
                    return False
            else:
                logger.error("❌ Falha na extração de dados")
                return False
                
        except Exception as e:
            logger.error(f"❌ Erro na atualização da base de dados: {str(e)}")
            return False
    
    async def initialize(self) -> bool:
        """Inicializa o sistema completo"""
        try:
            logger.info("🚀 Inicializando sistema de inteligência imobiliária...")
            
            # Verificar Firebase
            if not self.firebase_service.check_connection():
                logger.warning("⚠️ Firebase offline - usando modo degradado")
            
            # Carregar dados de imóveis
            await self.property_intelligence.load_property_data()
            
            logger.info("✅ Sistema iniciado com sucesso!")
            return True
            
        except Exception as e:
            logger.error(f"❌ Erro na inicialização: {str(e)}")
            return False


# Instância global do bot
intelligent_bot = IntelligentRealEstateBot()
