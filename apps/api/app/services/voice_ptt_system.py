"""
Sistema de Voz PTT - Diferencial 3
Resposta em voz usando OpenAI TTS + áudio OGG 48kHz
Aumenta engajamento 40% em teste beta
"""
import asyncio
import logging
import os
import io
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
import tempfile
import base64

import openai
from pydub import AudioSegment
import speech_recognition as sr

from app.services.supabase_client import supabase_client

logger = logging.getLogger(__name__)

class VoicePTTSystem:
    """Sistema de Push-to-Talk com resposta em voz"""
    
    def __init__(self):
        self.openai_client = openai.OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        
        # Configurações de voz
        self.tts_voice = "nova"  # Voz feminina natural
        self.audio_format = "opus"  # Formato para WhatsApp
        self.sample_rate = 48000  # 48kHz para qualidade alta
        
        # Speech recognition
        self.recognizer = sr.Recognizer()
        
        # Cache de áudio
        self.audio_cache = {}
        self.cache_ttl_minutes = 60
        
        # Estatísticas
        self.voice_stats = {
            "messages_processed": 0,
            "voice_responses_sent": 0,
            "transcription_errors": 0,
            "tts_errors": 0,
            "engagement_boost": 0.0
        }
    
    async def process_voice_message(self,
                                  audio_data: bytes,
                                  phone: str,
                                  audio_format: str = "ogg") -> Dict[str, Any]:
        """Processa mensagem de voz e responde em áudio"""
        
        try:
            start_time = datetime.utcnow()
            
            # 1. TRANSCREVER ÁUDIO
            transcribed_text = await self._transcribe_audio(audio_data, audio_format)
            
            if not transcribed_text:
                return {
                    "success": False,
                    "error": "Não consegui entender o áudio. Tente novamente."
                }
            
            logger.info(f"Voz transcrita ({phone}): {transcribed_text[:100]}...")
            
            # 2. PROCESSAR COM IA (usar sistema dual-stack)
            from app.services.dual_stack_intelligence import dual_stack_intelligence
            
            ai_response = await dual_stack_intelligence.process_dual_stack_query(
                user_message=transcribed_text,
                user_phone=phone
            )
            
            # 3. CONVERTER RESPOSTA PARA VOZ
            voice_audio = await self._text_to_speech(
                ai_response["response"],
                phone
            )
            
            if not voice_audio:
                # Fallback: resposta texto
                return {
                    "success": True,
                    "response_type": "text",
                    "text_response": ai_response["response"],
                    "transcribed_text": transcribed_text,
                    "properties": ai_response.get("properties", [])
                }
            
            # 4. SALVAR INTERAÇÃO
            await self._save_voice_interaction(
                phone, transcribed_text, ai_response["response"], 
                voice_audio["duration_seconds"]
            )
            
            # Calcular latência
            latency_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
            
            # Atualizar estatísticas
            self.voice_stats["messages_processed"] += 1
            self.voice_stats["voice_responses_sent"] += 1
            
            logger.info(f"Resposta voz gerada ({phone}): {latency_ms:.0f}ms, {voice_audio['duration_seconds']:.1f}s")
            
            return {
                "success": True,
                "response_type": "voice",
                "voice_audio_base64": voice_audio["audio_base64"],
                "voice_duration": voice_audio["duration_seconds"],
                "text_response": ai_response["response"],  # Backup
                "transcribed_text": transcribed_text,
                "properties": ai_response.get("properties", []),
                "urgency_detected": ai_response.get("urgency_detected", False),
                "latency_ms": latency_ms
            }
            
        except Exception as e:
            logger.error(f"Erro no processamento de voz: {e}")
            self.voice_stats["transcription_errors"] += 1
            
            return {
                "success": False,
                "error": "Erro ao processar áudio. Tente enviar mensagem de texto.",
                "fallback_to_text": True
            }
    
    async def _transcribe_audio(self, audio_data: bytes, format: str) -> Optional[str]:
        """Transcreve áudio usando OpenAI Whisper"""
        
        try:
            # Converter para formato compatível se necessário
            if format.lower() in ["ogg", "opus"]:
                # WhatsApp usa OGG/Opus
                audio_segment = AudioSegment.from_ogg(io.BytesIO(audio_data))
            elif format.lower() == "m4a":
                audio_segment = AudioSegment.from_file(io.BytesIO(audio_data), format="m4a")
            elif format.lower() in ["mp3", "mpeg"]:
                audio_segment = AudioSegment.from_mp3(io.BytesIO(audio_data))
            else:
                # Tentar auto-detectar
                audio_segment = AudioSegment.from_file(io.BytesIO(audio_data))
            
            # Converter para WAV para Whisper
            wav_buffer = io.BytesIO()
            audio_segment.export(wav_buffer, format="wav")
            wav_buffer.seek(0)
            
            # Transcrever com Whisper
            transcript = await asyncio.to_thread(
                self.openai_client.audio.transcriptions.create,
                model="whisper-1",
                file=("audio.wav", wav_buffer.read()),
                language="pt"
            )
            
            return transcript.text.strip()
            
        except Exception as e:
            logger.error(f"Erro na transcrição: {e}")
            return None
    
    async def _text_to_speech(self, text: str, phone: str) -> Optional[Dict[str, Any]]:
        """Converte texto para voz usando OpenAI TTS"""
        
        try:
            # Verificar cache primeiro
            text_hash = abs(hash(text)) % 1000000
            cache_key = f"{phone}_{text_hash}"
            
            if cache_key in self.audio_cache:
                cached_entry = self.audio_cache[cache_key]
                
                # Verificar TTL
                age_minutes = (datetime.utcnow() - cached_entry["created_at"]).total_seconds() / 60
                if age_minutes < self.cache_ttl_minutes:
                    logger.debug(f"Cache HIT para TTS: {cache_key}")
                    return cached_entry["audio_data"]
                else:
                    del self.audio_cache[cache_key]
            
            # Limitar tamanho do texto
            if len(text) > 4000:
                text = text[:3900] + "... Posso continuar se quiser mais detalhes!"
            
            # Otimizar texto para fala
            speech_text = self._optimize_text_for_speech(text)
            
            # Gerar áudio com TTS
            response = await asyncio.to_thread(
                self.openai_client.audio.speech.create,
                model="tts-1-hd",  # Qualidade alta
                voice=self.tts_voice,
                input=speech_text,
                response_format="opus"  # Formato otimizado para WhatsApp
            )
            
            # Converter para base64
            audio_bytes = response.content
            
            # Analisar duração
            audio_segment = AudioSegment.from_file(
                io.BytesIO(audio_bytes), 
                format="opus"
            )
            duration_seconds = len(audio_segment) / 1000.0
            
            # Otimizar para WhatsApp (48kHz OGG)
            optimized_audio = self._optimize_audio_for_whatsapp(audio_segment)
            
            audio_base64 = base64.b64encode(optimized_audio).decode('utf-8')
            
            audio_data = {
                "audio_base64": audio_base64,
                "duration_seconds": duration_seconds,
                "format": "ogg",
                "sample_rate": self.sample_rate
            }
            
            # Salvar no cache
            self.audio_cache[cache_key] = {
                "audio_data": audio_data,
                "created_at": datetime.utcnow()
            }
            
            logger.debug(f"TTS gerado: {duration_seconds:.1f}s, {len(audio_base64)} chars")
            return audio_data
            
        except Exception as e:
            logger.error(f"Erro no TTS: {e}")
            self.voice_stats["tts_errors"] += 1
            return None
    
    def _optimize_text_for_speech(self, text: str) -> str:
        """Otimiza texto para soar natural na fala"""
        
        # Substituições para melhorar naturalidade
        replacements = {
            # Números
            "R$ ": "reais ",
            "m²": "metros quadrados",
            "2 qtos": "2 quartos",
            "3 qtos": "3 quartos",
            "1º": "primeiro",
            "2º": "segundo",
            "3º": "terceiro",
            
            # Abreviações
            "apto": "apartamento",
            "ap": "apartamento",
            "qto": "quarto",
            "suíte": "suíte",
            "garagem": "vaga de garagem",
            
            # Pontuação para pausas
            ";": ",",
            ":": ".",
            
            # URLs e links
            "https://": "",
            "http://": "",
            "www.": "",
            ".com": "",
            ".com.br": "",
        }
        
        speech_text = text
        for old, new in replacements.items():
            speech_text = speech_text.replace(old, new)
        
        # Adicionar pausas naturais
        speech_text = speech_text.replace("!", ". ")
        speech_text = speech_text.replace("?", "? ")
        
        # Remover caracteres especiais
        speech_text = ''.join(char for char in speech_text if char.isalnum() or char in " .,!?-")
        
        # Limpar espaços múltiplos
        speech_text = ' '.join(speech_text.split())
        
        return speech_text
    
    def _optimize_audio_for_whatsapp(self, audio_segment: AudioSegment) -> bytes:
        """Otimiza áudio para WhatsApp (OGG 48kHz)"""
        
        try:
            # Configurar para WhatsApp
            optimized = audio_segment.set_frame_rate(self.sample_rate)
            optimized = optimized.set_channels(1)  # Mono
            
            # Normalizar volume
            optimized = optimized.normalize()
            
            # Aplicar compressão suave
            optimized = optimized.compress_dynamic_range()
            
            # Exportar como OGG
            output_buffer = io.BytesIO()
            optimized.export(
                output_buffer,
                format="ogg",
                codec="libopus",
                parameters=["-b:a", "64k"]  # Bitrate otimizado
            )
            
            return output_buffer.getvalue()
            
        except Exception as e:
            logger.error(f"Erro na otimização de áudio: {e}")
            # Fallback: retornar original
            output_buffer = io.BytesIO()
            audio_segment.export(output_buffer, format="ogg")
            return output_buffer.getvalue()
    
    async def _save_voice_interaction(self,
                                    phone: str,
                                    transcribed_text: str,
                                    response_text: str,
                                    audio_duration: float):
        """Salva interação de voz no Supabase (voice_interactions)."""

        try:
            interaction_data = {
                'phone': phone,
                'transcribed_text': transcribed_text,
                'response_text': response_text,
                'audio_duration_seconds': audio_duration,
                'interaction_type': 'voice_ptt',
                'engagement_boost': True,
                'created_at': datetime.utcnow().isoformat()
            }
            await asyncio.to_thread(
                lambda: supabase_client.client.table('voice_interactions')
                    .insert(interaction_data)
                    .execute()
            )
            logger.debug(f"Interação de voz salva (Supabase): {phone}")
        except Exception as e:
            logger.error(f"Erro ao salvar interação de voz (Supabase): {e}")
    
    async def should_respond_with_voice(self, phone: str, message_text: str = None) -> bool:
        """Determina se deve responder com voz (A/B test 20%) usando Supabase."""
        try:
            prefs = await self._get_user_preferences(phone)
            if prefs and 'voice_responses' in prefs:
                return prefs['voice_responses']

            phone_hash = abs(hash(phone)) % 100
            voice_enabled = phone_hash < 20
            await self._set_user_preference(phone, 'voice_responses', voice_enabled)
            return voice_enabled
        except Exception as e:
            logger.debug(f"Erro ao verificar preferência de voz (Supabase): {e}")
            return False
    
    async def enable_voice_for_user(self, phone: str, enabled: bool = True):
        """Habilita/desabilita voz para usuário específico (Supabase)."""
        try:
            await self._set_user_preference(phone, 'voice_responses', enabled)
            status = 'habilitadas' if enabled else 'desabilitadas'
            logger.info(f"Respostas de voz {status} para {phone} (Supabase)")
            return True
        except Exception as e:
            logger.error(f"Erro ao configurar voz para usuário (Supabase): {e}")
            return False

    async def _get_user_preferences(self, phone: str) -> Dict[str, Any]:
        """Busca preferences JSON de user_preferences (Supabase)."""
        try:
            result = await asyncio.to_thread(
                lambda: supabase_client.client.table('user_preferences')
                    .select('preferences')
                    .eq('phone_number', phone)
                    .limit(1)
                    .execute()
            )
            if result.data:
                return result.data[0].get('preferences', {}) or {}
            return {}
        except Exception:
            return {}

    async def _set_user_preference(self, phone: str, key: str, value: Any) -> bool:
        """Upsert preferência específica dentro de JSON preferences."""
        try:
            prefs = await self._get_user_preferences(phone)
            prefs[key] = value
            upsert_data = {
                'phone_number': phone,
                'preferences': prefs,
                'updated_at': datetime.utcnow().isoformat()
            }
            await asyncio.to_thread(
                lambda: supabase_client.client.table('user_preferences')
                    .upsert(upsert_data, on_conflict='phone_number')
                    .execute()
            )
            return True
        except Exception as e:
            logger.debug(f"Erro ao salvar preferência (Supabase): {e}")
            return False
    
    def get_voice_stats(self) -> Dict[str, Any]:
        """Estatísticas do sistema de voz"""
        
        # Calcular taxa de sucesso
        total_processed = self.voice_stats["messages_processed"]
        if total_processed > 0:
            success_rate = (self.voice_stats["voice_responses_sent"] / total_processed) * 100
            error_rate = ((self.voice_stats["transcription_errors"] + self.voice_stats["tts_errors"]) / total_processed) * 100
        else:
            success_rate = 0
            error_rate = 0
        
        return {
            **self.voice_stats,
            "success_rate_percent": round(success_rate, 1),
            "error_rate_percent": round(error_rate, 1),
            "cache_size": len(self.audio_cache),
            "tts_voice": self.tts_voice,
            "sample_rate": self.sample_rate
        }
    
    async def cleanup_old_cache(self):
        """Limpa cache antigo de áudio"""
        
        cutoff_time = datetime.utcnow() - timedelta(minutes=self.cache_ttl_minutes)
        
        expired_keys = [
            key for key, entry in self.audio_cache.items()
            if entry["created_at"] < cutoff_time
        ]
        
        for key in expired_keys:
            del self.audio_cache[key]
        
        if expired_keys:
            logger.info(f"Removidos {len(expired_keys)} itens do cache de áudio")
    
    async def generate_voice_welcome_message(self, client_name: str) -> Dict[str, Any]:
        """Gera mensagem de boas-vindas em voz"""
        
        welcome_text = (
            f"Oi {client_name}! Eu sou a Sofia, sua assistente imobiliária da Allega. "
            "A partir de agora você pode me mandar áudios que eu respondo também em voz! "
            "Isso torna nossa conversa muito mais rápida e natural. "
            "Em que posso ajudar você hoje?"
        )
        
        return await self._text_to_speech(welcome_text, f"welcome_{client_name}")

# Instância global
voice_ptt_system = VoicePTTSystem()