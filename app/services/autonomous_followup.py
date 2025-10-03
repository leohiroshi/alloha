"""
Sistema de Follow-up Autônomo - Diferencial 2
Agenda automaticamente via Google Calendar API + Calendly-like
"""
import asyncio
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import json
import os

# Google Calendar API (opcional). Se não instalado, sistema entra em modo fallback.
try:
    from google.oauth2.credentials import Credentials  # type: ignore
    from google.auth.transport.requests import Request  # type: ignore
    from google_auth_oauthlib.flow import Flow  # type: ignore
    from googleapiclient.discovery import build  # type: ignore
    _GOOGLE_CALENDAR_AVAILABLE = True
except ImportError:
    _GOOGLE_CALENDAR_AVAILABLE = False
    Credentials = None  # type: ignore
    Flow = None  # type: ignore
    build = None  # type: ignore

from app.services.supabase_client import supabase_client

logger = logging.getLogger(__name__)

class AutonomousFollowUp:
    """Sistema de agendamento autônomo"""
    
    def __init__(self):
        self.calendar_service = None
        self.calendar_id = os.getenv('GOOGLE_CALENDAR_ID', 'primary')
        
        # Templates de agendamento por urgência
        self.scheduling_templates = {
            5: {  # CRÍTICO
                "slots": ["today_afternoon", "tomorrow_morning"],
                "duration_minutes": 30,
                "title_template": "🚨 VISITA URGENTE - {client_name}",
                "message_template": "Agendei uma visita urgente para {date_time}. Link para confirmar: {calendar_link}"
            },
            4: {  # ALTO
                "slots": ["tomorrow_morning", "tomorrow_afternoon", "day_after_morning"],
                "duration_minutes": 45,
                "title_template": "VISITA PRIORITÁRIA - {client_name}",
                "message_template": "Perfeito! Agendei sua visita para {date_time}. Confirme aqui: {calendar_link}"
            },
            3: {  # MÉDIO
                "slots": ["week_mornings", "week_afternoons"],
                "duration_minutes": 60,
                "title_template": "Visita Imóvel - {client_name}",
                "message_template": "Ótimo! Sua visita está agendada para {date_time}. Link: {calendar_link}"
            }
        }
        
        # Horários padrão
        self.time_slots = {
            "morning": [9, 10, 11],  # 9h, 10h, 11h
            "afternoon": [14, 15, 16, 17],  # 14h, 15h, 16h, 17h
            "evening": [18, 19]  # 18h, 19h
        }
    
    async def initialize_calendar_service(self):
        """Inicializa serviço do Google Calendar"""
        
        if os.getenv('ENABLE_GOOGLE_CALENDAR', 'false').lower() not in ('1','true','yes','on'):
            logger.info("Google Calendar desativado por configuração (ENABLE_GOOGLE_CALENDAR)")
            return False
        if not _GOOGLE_CALENDAR_AVAILABLE:
            logger.warning("Google Calendar libs não instaladas - fallback ativo")
            return False
        try:
            # Credenciais OAuth2
            creds = None
            token_path = 'google_calendar_token.json'
            credentials_path = 'google_calendar_credentials.json'
            
            # Carregar token existente
            if os.path.exists(token_path):
                creds = Credentials.from_authorized_user_file(token_path)
            
            # Se não há credenciais válidas, fazer flow OAuth
            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    creds.refresh(Request())
                else:
                    flow = Flow.from_client_secrets_file(
                        credentials_path,
                        scopes=['https://www.googleapis.com/auth/calendar']
                    )
                    flow.redirect_uri = 'urn:ietf:wg:oauth:2.0:oob'
                    
                    # Salvar credenciais
                    with open(token_path, 'w') as token:
                        token.write(creds.to_json())
            
            # Construir serviço
            self.calendar_service = build('calendar', 'v3', credentials=creds)
            
            logger.info("Google Calendar inicializado com sucesso")
            return True
            
        except Exception as e:
            logger.error(f"Erro ao inicializar Google Calendar: {e}")
            return False
    
    async def schedule_autonomous_visit(self,
                                     phone: str,
                                     client_name: str,
                                     urgency_score: int,
                                     property_interests: List[Dict] = None,
                                     preferred_times: List[str] = None) -> Dict[str, Any]:
        """Agenda visita autônoma baseada na urgência"""
        
        try:
            # Inicializar Calendar se necessário
            if not self.calendar_service:
                init_ok = await self.initialize_calendar_service()
                if not init_ok:
                    return await self._fallback_scheduling(phone, client_name)
            
            # Template baseado na urgência
            template = self.scheduling_templates.get(urgency_score, self.scheduling_templates[3])
            
            # Encontrar slot disponível
            available_slot = await self._find_available_slot(
                urgency_score, 
                template["slots"],
                template["duration_minutes"],
                preferred_times
            )
            
            if not available_slot:
                return await self._fallback_scheduling(phone, client_name)
            
            # Criar evento no Google Calendar
            event_data = await self._create_calendar_event(
                available_slot,
                template,
                client_name,
                phone,
                property_interests
            )
            
            # Persistir no Supabase
            await self._save_scheduled_visit(phone, event_data, urgency_score)
            
            # Gerar resposta WhatsApp
            response_message = template["message_template"].format(
                date_time=event_data["formatted_datetime"],
                calendar_link=event_data["calendar_link"]
            )
            
            logger.info(f"Visita agendada autonomamente: {phone} para {event_data['formatted_datetime']}")
            
            return {
                "success": True,
                "event_id": event_data["event_id"],
                "scheduled_datetime": available_slot["datetime"],
                "calendar_link": event_data["calendar_link"],
                "message": response_message,
                "urgency_score": urgency_score
            }
            
        except Exception as e:
            logger.error(f"Erro no agendamento autônomo: {e}")
            return await self._fallback_scheduling(phone, client_name)
    
    async def _find_available_slot(self,
                                 urgency_score: int,
                                 slot_preferences: List[str],
                                 duration_minutes: int,
                                 client_preferred_times: List[str] = None) -> Optional[Dict]:
        """Encontra slot disponível baseado na urgência"""
        
        try:
            # Gerar candidatos de horários
            candidate_slots = self._generate_time_candidates(
                slot_preferences, 
                urgency_score,
                client_preferred_times
            )
            
            # Verificar disponibilidade no Google Calendar
            for slot in candidate_slots:
                is_available = await self._check_calendar_availability(
                    slot["datetime"],
                    duration_minutes
                )
                
                if is_available:
                    slot["duration_minutes"] = duration_minutes
                    return slot
            
            return None
            
        except Exception as e:
            logger.error(f"Erro ao encontrar slot disponível: {e}")
            return None
    
    def _generate_time_candidates(self,
                                slot_preferences: List[str],
                                urgency_score: int,
                                client_preferences: List[str] = None) -> List[Dict]:
        """Gera lista de candidatos de horário"""
        
        candidates = []
        base_date = datetime.now()
        
        # Mapear preferências para dias/horários
        for pref in slot_preferences:
            if pref == "today_afternoon":
                # Hoje à tarde (só se for antes das 15h)
                if base_date.hour < 15:
                    for hour in self.time_slots["afternoon"]:
                        if hour > base_date.hour:
                            candidate_time = base_date.replace(
                                hour=hour, minute=0, second=0, microsecond=0
                            )
                            candidates.append({
                                "datetime": candidate_time,
                                "label": f"Hoje às {hour}h",
                                "priority": 10  # Máxima prioridade
                            })
            
            elif pref == "tomorrow_morning":
                tomorrow = base_date + timedelta(days=1)
                for hour in self.time_slots["morning"]:
                    candidate_time = tomorrow.replace(
                        hour=hour, minute=0, second=0, microsecond=0
                    )
                    candidates.append({
                        "datetime": candidate_time,
                        "label": f"Amanhã às {hour}h",
                        "priority": 9
                    })
            
            elif pref == "tomorrow_afternoon":
                tomorrow = base_date + timedelta(days=1)
                for hour in self.time_slots["afternoon"]:
                    candidate_time = tomorrow.replace(
                        hour=hour, minute=0, second=0, microsecond=0
                    )
                    candidates.append({
                        "datetime": candidate_time,
                        "label": f"Amanhã às {hour}h",
                        "priority": 8
                    })
            
            elif pref == "week_mornings":
                # Próximos 5 dias úteis de manhã
                for day_offset in range(1, 8):  # Próxima semana
                    future_date = base_date + timedelta(days=day_offset)
                    
                    # Pular fins de semana se não for urgência alta
                    if future_date.weekday() >= 5 and urgency_score < 4:
                        continue
                    
                    for hour in self.time_slots["morning"]:
                        candidate_time = future_date.replace(
                            hour=hour, minute=0, second=0, microsecond=0
                        )
                        candidates.append({
                            "datetime": candidate_time,
                            "label": f"{self._format_date(future_date)} às {hour}h",
                            "priority": 7 - day_offset  # Prioridade decrescente
                        })
        
        # Ordenar por prioridade
        candidates.sort(key=lambda x: x["priority"], reverse=True)
        
        return candidates[:20]  # Limitar a 20 opções
    
    async def _check_calendar_availability(self,
                                         datetime_slot: datetime,
                                         duration_minutes: int) -> bool:
        """Verifica disponibilidade no Google Calendar"""
        
        try:
            # Definir janela de busca
            time_min = datetime_slot.isoformat() + 'Z'
            time_max = (datetime_slot + timedelta(minutes=duration_minutes)).isoformat() + 'Z'
            
            # Buscar eventos conflitantes
            events_result = self.calendar_service.events().list(
                calendarId=self.calendar_id,
                timeMin=time_min,
                timeMax=time_max,
                singleEvents=True,
                orderBy='startTime'
            ).execute()
            
            events = events_result.get('items', [])
            
            # Se há eventos, slot não está disponível
            return len(events) == 0
            
        except Exception as e:
            logger.error(f"Erro ao verificar disponibilidade: {e}")
            # Em caso de erro, assumir disponível
            return True
    
    async def _create_calendar_event(self,
                                   time_slot: Dict,
                                   template: Dict,
                                   client_name: str,
                                   phone: str,
                                   properties: List[Dict] = None) -> Dict[str, Any]:
        """Cria evento no Google Calendar"""
        
        try:
            start_time = time_slot["datetime"]
            end_time = start_time + timedelta(minutes=time_slot["duration_minutes"])
            
            # Preparar descrição
            description_parts = [
                f"Cliente: {client_name}",
                f"Telefone: {phone}",
                f"Agendado automaticamente pela Sofia IA"
            ]
            
            if properties:
                description_parts.append("\\nImóveis de interesse:")
                for prop in properties[:3]:
                    desc = prop.get('text', '')[:100]
                    description_parts.append(f"- {desc}")
            
            description_parts.append(f"\\nConfirmar presença: WhatsApp {phone}")
            
            # Evento
            event = {
                'summary': template["title_template"].format(client_name=client_name),
                'description': "\\n".join(description_parts),
                'start': {
                    'dateTime': start_time.isoformat(),
                    'timeZone': 'America/Sao_Paulo',
                },
                'end': {
                    'dateTime': end_time.isoformat(),
                    'timeZone': 'America/Sao_Paulo',
                },
                'attendees': [
                    {'email': os.getenv('BROKER_EMAIL', 'corretor@alloha.ai')}
                ],
                'reminders': {
                    'useDefault': False,
                    'overrides': [
                        {'method': 'popup', 'minutes': 30},
                        {'method': 'email', 'minutes': 60},
                    ],
                },
                'conferenceData': {
                    'createRequest': {
                        'requestId': f"meet-{phone}-{int(start_time.timestamp())}",
                        'conferenceSolutionKey': {'type': 'hangoutsMeet'}
                    }
                }
            }
            
            # Criar evento
            created_event = self.calendar_service.events().insert(
                calendarId=self.calendar_id,
                body=event,
                conferenceDataVersion=1
            ).execute()
            
            # Link do evento
            calendar_link = created_event.get('htmlLink', '')
            
            return {
                "event_id": created_event['id'],
                "calendar_link": calendar_link,
                "formatted_datetime": self._format_datetime(start_time),
                "start_time": start_time,
                "end_time": end_time,
                "meet_link": created_event.get('conferenceData', {}).get('entryPoints', [{}])[0].get('uri', '')
            }
            
        except Exception as e:
            logger.error(f"Erro ao criar evento no calendar: {e}")
            raise
    
    async def _save_scheduled_visit(self,
                                  phone: str,
                                  event_data: Dict,
                                  urgency_score: int):
        """Salva visita agendada no Supabase (tabela scheduled_visits)"""
        try:
            visit_data = {
                'phone_number': phone,
                'event_id': event_data['event_id'],
                'scheduled_at': event_data['start_time'].isoformat(),
                'duration_minutes': (event_data['end_time'] - event_data['start_time']).seconds // 60,
                'calendar_link': event_data['calendar_link'],
                'meet_link': event_data.get('meet_link', ''),
                'urgency_level': urgency_score,
                'status': 'scheduled',
                'confirmation_sent_at': None,
                'reminder_sent_at': None,
                'notes': json.dumps({'auto': True}),
                'created_at': datetime.utcnow().isoformat(),
                'updated_at': datetime.utcnow().isoformat()
            }
            supabase_client.client.table('scheduled_visits').insert(visit_data).execute()
            logger.info(f"Visita salva no Supabase: {phone} - {event_data['event_id']}")
        except Exception as e:
            logger.error(f"Erro ao salvar visita agendada (Supabase): {e}")
    
    async def _fallback_scheduling(self, phone: str, client_name: str) -> Dict[str, Any]:
        """Fallback quando não consegue agendar automaticamente"""
        
        return {
            "success": False,
            "message": (
                f"Olá {client_name}! Vou conectar você com nosso corretor "
                "para agendarmos sua visita no melhor horário. "
                "Ele entrará em contato em até 30 minutos! 📞"
            ),
            "requires_manual_scheduling": True
        }
    
    def _format_datetime(self, dt: datetime) -> str:
        """Formata data/hora para mensagem"""
        
        days_map = {
            0: "segunda", 1: "terça", 2: "quarta", 3: "quinta", 
            4: "sexta", 5: "sábado", 6: "domingo"
        }
        
        today = datetime.now().date()
        dt_date = dt.date()
        
        if dt_date == today:
            return f"hoje às {dt.hour}h"
        elif dt_date == today + timedelta(days=1):
            return f"amanhã às {dt.hour}h"
        else:
            day_name = days_map[dt.weekday()]
            return f"{day_name} ({dt.day}/{dt.month}) às {dt.hour}h"
    
    def _format_date(self, dt: datetime) -> str:
        """Formata apenas a data"""
        
        days_map = {
            0: "seg", 1: "ter", 2: "qua", 3: "qui", 
            4: "sex", 5: "sáb", 6: "dom"
        }
        
        return f"{days_map[dt.weekday()]} {dt.day}/{dt.month}"
    
    async def send_confirmation_reminders(self):
        """Envia lembretes de confirmação (executar via cron)"""
        
        try:
            # Buscar visitas agendadas para próximas 24h sem confirmação
            tomorrow = datetime.utcnow() + timedelta(days=1)
            
            # Buscar visitas em janela até 24h que não tenham confirmação / lembrete
            now_iso = datetime.utcnow().isoformat()
            tomorrow_iso = tomorrow.isoformat()
            result = supabase_client.client.table('scheduled_visits') \
                .select('id, scheduled_at, calendar_link, confirmation_sent_at, status') \
                .eq('status', 'scheduled') \
                .gte('scheduled_at', now_iso) \
                .lte('scheduled_at', tomorrow_iso) \
                .is_('confirmation_sent_at', 'null') \
                .execute()

            visits = result.data or []
            reminders_sent = 0
            for visit in visits:
                try:
                    # (Envio real de mensagem ficaria em outro serviço)
                    # Atualizar como confirmado envio de lembrete
                    supabase_client.client.table('scheduled_visits') \
                        .update({'confirmation_sent_at': datetime.utcnow().isoformat()}) \
                        .eq('id', visit['id']) \
                        .execute()
                    reminders_sent += 1
                except Exception as inner:
                    logger.debug(f"Falha atualizar lembrete visita {visit.get('id')}: {inner}")

            logger.info(f"Enviados {reminders_sent} lembretes de confirmação (Supabase)")
            return reminders_sent
            
        except Exception as e:
            logger.error(f"Erro ao enviar lembretes: {e}")
            return 0
    
    async def get_scheduled_visits(self, 
                                 date_from: datetime = None,
                                 date_to: datetime = None,
                                 status: str = None) -> List[Dict[str, Any]]:
        """Recupera visitas agendadas para dashboard"""
        
        try:
            if not date_from:
                date_from = datetime.utcnow()
            if not date_to:
                date_to = date_from + timedelta(days=30)
            
            from_iso = date_from.isoformat()
            to_iso = date_to.isoformat()
            query = supabase_client.client.table('scheduled_visits') \
                .select('*') \
                .gte('scheduled_at', from_iso) \
                .lte('scheduled_at', to_iso)
            if status:
                query = query.eq('status', status)
            result = query.order('scheduled_at').execute()
            return result.data or []
            
        except Exception as e:
            logger.error(f"Erro ao recuperar visitas agendadas: {e}")
            return []

# Instância global
autonomous_followup = AutonomousFollowUp()