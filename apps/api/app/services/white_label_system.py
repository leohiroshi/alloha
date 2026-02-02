"""
Sistema White-Label Instantâneo - Diferencial 5
Gera subdomínio imobiliariaX.alloha.ai em 3 minutos
"""
import asyncio
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
import json
import os
import string
import secrets

import aiohttp
from jinja2 import Template

from app.services.supabase_client import supabase_client

logger = logging.getLogger(__name__)

class WhiteLabelSystem:
    """Sistema de white-label instantâneo"""
    
    def __init__(self):
        # Configurações do sistema
        self.base_domain = "alloha.ai"
        self.cdn_url = os.getenv("CDN_URL", "https://cdn.alloha.ai")
        self.template_bucket = os.getenv("TEMPLATE_BUCKET", "alloha-templates")
        
        # Configurações de DNS (Cloudflare)
        self.cloudflare_config = {
            "zone_id": os.getenv("CLOUDFLARE_ZONE_ID"),
            "api_token": os.getenv("CLOUDFLARE_API_TOKEN"),
            "enabled": bool(os.getenv("CLOUDFLARE_API_TOKEN"))
        }
        
        # Templates disponíveis
        self.available_templates = {
            "modern": {
                "name": "Moderno",
                "description": "Design clean e moderno",
                "preview_url": f"{self.cdn_url}/templates/modern/preview.png",
                "config": {
                    "primary_color": "#2563eb",
                    "secondary_color": "#64748b",
                    "accent_color": "#f59e0b",
                    "font_family": "Inter"
                }
            },
            "classic": {
                "name": "Clássico",
                "description": "Design tradicional e elegante",
                "preview_url": f"{self.cdn_url}/templates/classic/preview.png",
                "config": {
                    "primary_color": "#1e40af",
                    "secondary_color": "#374151",
                    "accent_color": "#dc2626",
                    "font_family": "Roboto"
                }
            },
            "luxury": {
                "name": "Luxo",
                "description": "Design sofisticado para imóveis de alto padrão",
                "preview_url": f"{self.cdn_url}/templates/luxury/preview.png",
                "config": {
                    "primary_color": "#000000",
                    "secondary_color": "#6b7280",
                    "accent_color": "#fbbf24",
                    "font_family": "Playfair Display"
                }
            }
        }
        
        # Estatísticas
        self.deployment_stats = {
            "total_deployments": 0,
            "active_sites": 0,
            "average_deployment_time": 0.0,
            "success_rate": 0.0,
            "last_deployment": None
        }
    
    async def create_white_label_site(self,
                                    company_name: str,
                                    company_email: str,
                                    template_id: str = "modern",
                                    custom_domain: str = None,
                                    branding: Dict[str, Any] = None) -> Dict[str, Any]:
        """Cria site white-label em menos de 3 minutos"""
        
        start_time = datetime.utcnow()
        
        try:
            logger.info(f"Iniciando criação white-label para {company_name}")
            
            # 1. VALIDAR E PREPARAR DADOS
            validation_result = await self._validate_deployment_data(
                company_name, company_email, template_id, custom_domain
            )
            
            if not validation_result["valid"]:
                return {
                    "success": False,
                    "error": validation_result["error"],
                    "deployment_time": 0
                }
            
            # 2. GERAR SUBDOMÍNIO
            subdomain = await self._generate_subdomain(company_name)
            full_domain = f"{subdomain}.{self.base_domain}"
            
            # 3. CONFIGURAR DNS
            dns_result = await self._setup_dns_record(subdomain)
            if not dns_result["success"]:
                return {
                    "success": False,
                    "error": f"Erro DNS: {dns_result['error']}",
                    "deployment_time": 0
                }
            
            # 4. GERAR CONFIGURAÇÃO DO SITE
            site_config = await self._generate_site_config(
                company_name, company_email, template_id, branding, subdomain
            )
            
            # 5. DEPLOYAR TEMPLATE
            deployment_result = await self._deploy_template(
                subdomain, template_id, site_config
            )
            
            if not deployment_result["success"]:
                # Rollback DNS se deploy falhou
                await self._cleanup_dns_record(subdomain)
                return {
                    "success": False,
                    "error": f"Erro no deploy: {deployment_result['error']}",
                    "deployment_time": 0
                }
            
            # 6. CONFIGURAR SSL
            ssl_result = await self._setup_ssl_certificate(full_domain)
            
            # 7. SALVAR CONFIGURAÇÃO
            site_data = await self._save_site_configuration(
                subdomain, company_name, company_email, template_id, site_config
            )
            
            # 8. CONFIGURAR INTEGRAÇÃO WHATSAPP
            whatsapp_config = await self._setup_whatsapp_integration(
                subdomain, site_data["site_id"]
            )
            
            # Calcular tempo total
            deployment_time = (datetime.utcnow() - start_time).total_seconds()
            
            # Atualizar estatísticas
            self.deployment_stats["total_deployments"] += 1
            self.deployment_stats["active_sites"] += 1
            self.deployment_stats["average_deployment_time"] = (
                (self.deployment_stats["average_deployment_time"] + deployment_time) / 2
            )
            self.deployment_stats["last_deployment"] = datetime.utcnow()
            
            logger.info(f"Site white-label criado: {full_domain} em {deployment_time:.1f}s")
            
            return {
                "success": True,
                "site_url": f"https://{full_domain}",
                "admin_url": f"https://{full_domain}/admin",
                "subdomain": subdomain,
                "site_id": site_data["site_id"],
                "template_used": template_id,
                "whatsapp_webhook": whatsapp_config["webhook_url"],
                "deployment_time": deployment_time,
                "ssl_enabled": ssl_result["success"],
                "features": {
                    "custom_branding": True,
                    "whatsapp_integration": True,
                    "property_showcase": True,
                    "lead_capture": True,
                    "analytics": True
                }
            }
            
        except Exception as e:
            logger.error(f"Erro na criação white-label: {e}")
            
            # Cleanup em caso de erro
            if 'subdomain' in locals():
                await self._cleanup_failed_deployment(subdomain)
            
            return {
                "success": False,
                "error": str(e),
                "deployment_time": (datetime.utcnow() - start_time).total_seconds()
            }
    
    async def _validate_deployment_data(self,
                                      company_name: str,
                                      email: str,
                                      template_id: str,
                                      custom_domain: str = None) -> Dict[str, Any]:
        """Valida dados para deployment"""
        
        # Validar nome da empresa
        if not company_name or len(company_name.strip()) < 2:
            return {"valid": False, "error": "Nome da empresa deve ter pelo menos 2 caracteres"}
        
        # Validar email
        if not email or "@" not in email:
            return {"valid": False, "error": "Email inválido"}
        
        # Validar template
        if template_id not in self.available_templates:
            return {"valid": False, "error": f"Template '{template_id}' não existe"}
        
        # Validar domínio customizado se fornecido
        if custom_domain:
            if not self._is_valid_domain(custom_domain):
                return {"valid": False, "error": "Domínio customizado inválido"}
        
        return {"valid": True}
    
    async def _generate_subdomain(self, company_name: str) -> str:
        """Gera subdomínio único baseado no nome da empresa"""
        
        # Sanitizar nome da empresa
        safe_name = ''.join(c for c in company_name.lower() if c.isalnum())
        safe_name = safe_name[:15]  # Limitar tamanho
        
        # Verificar disponibilidade
        base_subdomain = safe_name
        counter = 1
        
        while await self._subdomain_exists(base_subdomain):
            base_subdomain = f"{safe_name}{counter}"
            counter += 1
            
            if counter > 100:  # Fallback
                base_subdomain = f"{safe_name}{secrets.token_hex(4)}"
                break
        
        return base_subdomain
    
    async def _subdomain_exists(self, subdomain: str) -> bool:
        """Verifica se subdomínio já existe (Supabase)."""
        try:
            result = await asyncio.to_thread(
                lambda: supabase_client.client.table('white_label_sites')
                    .select('site_id')
                    .eq('subdomain', subdomain)
                    .limit(1)
                    .execute()
            )
            return bool(result.data)
        except Exception as e:
            logger.debug(f"Erro ao verificar subdomínio no Supabase: {e}")
            return False
    
    async def _setup_dns_record(self, subdomain: str) -> Dict[str, Any]:
        """Configura registro DNS no Cloudflare"""
        
        if not self.cloudflare_config["enabled"]:
            logger.warning("Cloudflare não configurado, pulando DNS")
            return {"success": True, "message": "DNS simulado"}
        
        try:
            headers = {
                "Authorization": f"Bearer {self.cloudflare_config['api_token']}",
                "Content-Type": "application/json"
            }
            
            # Criar registro CNAME
            dns_record = {
                "type": "CNAME",
                "name": subdomain,
                "content": "app.alloha.ai",  # Aponta para servidor principal
                "ttl": 300,  # 5 minutos
                "proxied": True  # Usar proxy do Cloudflare
            }
            
            url = f"https://api.cloudflare.com/client/v4/zones/{self.cloudflare_config['zone_id']}/dns_records"
            
            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=headers, json=dns_record) as response:
                    if response.status == 200:
                        result = await response.json()
                        
                        return {
                            "success": True,
                            "dns_record_id": result["result"]["id"],
                            "message": f"DNS configurado para {subdomain}.{self.base_domain}"
                        }
                    else:
                        error_data = await response.json()
                        return {
                            "success": False,
                            "error": error_data.get("errors", [{}])[0].get("message", "Erro DNS")
                        }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _generate_site_config(self,
                                  company_name: str,
                                  email: str,
                                  template_id: str,
                                  branding: Dict[str, Any],
                                  subdomain: str) -> Dict[str, Any]:
        """Gera configuração completa do site"""
        
        # Configuração base do template
        base_config = self.available_templates[template_id]["config"].copy()
        
        # Aplicar branding customizado
        if branding:
            base_config.update(branding)
        
        # Configuração completa
        site_config = {
            "company": {
                "name": company_name,
                "email": email,
                "subdomain": subdomain
            },
            "branding": base_config,
            "features": {
                "property_search": True,
                "whatsapp_chat": True,
                "lead_forms": True,
                "virtual_tours": True,
                "financing_calculator": True,
                "broker_profiles": True
            },
            "integrations": {
                "whatsapp_api": True,
                "google_analytics": True,
                "facebook_pixel": True,
                "crm_sync": True
            },
            "seo": {
                "title": f"{company_name} - Imóveis",
                "description": f"Encontre o imóvel ideal com {company_name}. Casas e apartamentos para venda e locação.",
                "keywords": f"{company_name}, imóveis, casas, apartamentos, {subdomain}",
                "robots": "index, follow"
            },
            "performance": {
                "cache_ttl": 3600,
                "image_optimization": True,
                "lazy_loading": True,
                "compression": True
            }
        }
        
        return site_config
    
    async def _deploy_template(self,
                             subdomain: str,
                             template_id: str,
                             config: Dict[str, Any]) -> Dict[str, Any]:
        """Deploya template com configuração"""
        
        try:
            # Aqui você integraria com serviços como:
            # - Vercel/Netlify para deploy estático
            # - Docker containers
            # - Kubernetes pods
            # - FlutterFlow API (mencionado no requisito)
            
            # Simulação do processo de deploy
            logger.info(f"Deployando template {template_id} para {subdomain}")
            
            # Gerar arquivos de configuração
            config_files = await self._generate_template_files(template_id, config)
            
            # Deploy simulado (substitua pela integração real)
            await asyncio.sleep(2)  # Simula tempo de deploy
            
            return {
                "success": True,
                "deployment_id": f"deploy_{subdomain}_{int(datetime.utcnow().timestamp())}",
                "files_generated": len(config_files),
                "message": f"Template {template_id} deployado com sucesso"
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _generate_template_files(self,
                                     template_id: str,
                                     config: Dict[str, Any]) -> List[str]:
        """Gera arquivos do template com configurações"""
        
        template_files = []
        
        try:
            # Template HTML principal
            html_template = Template('''
            <!DOCTYPE html>
            <html lang="pt-BR">
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>{{ config.seo.title }}</title>
                <meta name="description" content="{{ config.seo.description }}">
                <meta name="keywords" content="{{ config.seo.keywords }}">
                <link href="https://fonts.googleapis.com/css2?family={{ config.branding.font_family }}:wght@300;400;500;600;700&display=swap" rel="stylesheet">
                <style>
                    :root {
                        --primary-color: {{ config.branding.primary_color }};
                        --secondary-color: {{ config.branding.secondary_color }};
                        --accent-color: {{ config.branding.accent_color }};
                        --font-family: '{{ config.branding.font_family }}', sans-serif;
                    }
                </style>
            </head>
            <body>
                <!-- Template content será injetado aqui -->
                <div id="app"></div>
                
                <!-- WhatsApp Integration -->
                <div id="whatsapp-chat" data-subdomain="{{ config.company.subdomain }}"></div>
                
                <script src="{{ cdn_url }}/templates/{{ template_id }}/app.js"></script>
            </body>
            </html>
            ''')
            
            rendered_html = html_template.render(
                config=config,
                template_id=template_id,
                cdn_url=self.cdn_url
            )
            
            template_files.append("index.html")
            
            # Configuração JavaScript
            js_config = {
                "api_base_url": f"https://api.alloha.ai/v1/sites/{config['company']['subdomain']}",
                "whatsapp_integration": True,
                "company": config["company"],
                "branding": config["branding"],
                "features": config["features"]
            }
            
            template_files.append("config.js")
            
            logger.info(f"Gerados {len(template_files)} arquivos para {template_id}")
            return template_files
            
        except Exception as e:
            logger.error(f"Erro ao gerar arquivos do template: {e}")
            return []
    
    async def _setup_ssl_certificate(self, domain: str) -> Dict[str, Any]:
        """Configura certificado SSL"""
        
        try:
            # Com Cloudflare proxy, SSL é automático
            # Aqui você integraria com Let's Encrypt ou similar
            
            await asyncio.sleep(1)  # Simula tempo de configuração SSL
            
            return {
                "success": True,
                "certificate_type": "cloudflare_universal",
                "expires_at": datetime.utcnow().replace(year=datetime.utcnow().year + 1)
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _save_site_configuration(self,
                                     subdomain: str,
                                     company_name: str,
                                     email: str,
                                     template_id: str,
                                     config: Dict[str, Any]) -> Dict[str, Any]:
        """Salva configuração do site no Supabase (tabela white_label_sites)."""

        try:
            site_id = f"site_{subdomain}_{secrets.token_hex(8)}"
            now_iso = datetime.utcnow().isoformat()
            site_data = {
                'site_id': site_id,
                'subdomain': subdomain,
                'full_domain': f"{subdomain}.{self.base_domain}",
                'company_name': company_name,
                'company_email': email,
                'template_id': template_id,
                'config': config,  # Armazenado como JSONB
                'status': 'active',
                'created_at': now_iso,
                'last_updated': now_iso,
                'deployment_version': '1.0.0',
                'analytics': {
                    'page_views': 0,
                    'unique_visitors': 0,
                    'leads_generated': 0,
                    'whatsapp_clicks': 0
                }
            }

            # Insert
            result = await asyncio.to_thread(
                lambda: supabase_client.client.table('white_label_sites')
                    .insert(site_data)
                    .execute()
            )

            if result.data:
                return result.data[0]
            return site_data
        except Exception as e:
            logger.error(f"Erro ao salvar configuração do site (Supabase): {e}")
            raise
    
    async def _setup_whatsapp_integration(self, subdomain: str, site_id: str) -> Dict[str, Any]:
        """Configura integração WhatsApp para o site (Supabase)."""
        try:
            webhook_url = f"https://api.alloha.ai/webhook/whatsapp/{site_id}"
            whatsapp_config = {
                'webhook_url': webhook_url,
                'site_id': site_id,
                'subdomain': subdomain,
                'enabled': True,
                'auto_responses': True,
                'lead_routing': 'auto',
                'created_at': datetime.utcnow().isoformat()
            }
            await asyncio.to_thread(
                lambda: supabase_client.client.table('whatsapp_integrations')
                    .upsert(whatsapp_config, on_conflict='site_id')
                    .execute()
            )
            return whatsapp_config
        except Exception as e:
            logger.error(f"Erro na integração WhatsApp (Supabase): {e}")
            return {'webhook_url': '', 'enabled': False}
    
    async def get_available_templates(self) -> List[Dict[str, Any]]:
        """Retorna templates disponíveis"""
        
        templates = []
        
        for template_id, template_data in self.available_templates.items():
            templates.append({
                "id": template_id,
                **template_data,
                "deployment_time_estimate": "2-3 minutos"
            })
        
        return templates
    
    async def get_site_analytics(self, site_id: str) -> Dict[str, Any]:
        """Recupera analytics do site (Supabase)."""
        try:
            result = await asyncio.to_thread(
                lambda: supabase_client.client.table('white_label_sites')
                    .select('*')
                    .eq('site_id', site_id)
                    .limit(1)
                    .execute()
            )
            if not result.data:
                return {'error': 'Site não encontrado'}
            site_data = result.data[0]
            return {
                'site_info': {
                    'subdomain': site_data.get('subdomain'),
                    'company_name': site_data.get('company_name'),
                    'status': site_data.get('status'),
                    'created_at': site_data.get('created_at')
                },
                'analytics': site_data.get('analytics', {}),
                'performance': {
                    'uptime_percent': 99.9,
                    'avg_response_time_ms': 250,
                    'ssl_status': 'active'
                }
            }
        except Exception as e:
            logger.error(f"Erro ao obter analytics (Supabase): {e}")
            return {'error': str(e)}
    
    def _is_valid_domain(self, domain: str) -> bool:
        """Valida formato de domínio"""
        
        import re
        pattern = r'^[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?)*$'
        return re.match(pattern, domain) is not None
    
    async def _cleanup_dns_record(self, subdomain: str):
        """Remove registro DNS em caso de falha"""
        
        logger.info(f"Limpando DNS para {subdomain}")
        # Implementar remoção do registro DNS
    
    async def _cleanup_failed_deployment(self, subdomain: str):
        """Limpa recursos de deployment falhado"""
        
        logger.info(f"Limpando deployment falhado para {subdomain}")
        # Implementar limpeza completa
    
    def get_deployment_stats(self) -> Dict[str, Any]:
        """Estatísticas de deployments"""
        
        return {
            **self.deployment_stats,
            "available_templates": len(self.available_templates),
            "avg_deployment_time_formatted": f"{self.deployment_stats['average_deployment_time']:.1f}s"
        }

# Instância global
white_label_system = WhiteLabelSystem()