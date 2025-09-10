"""
Teste para verificar capacidades de análise de imagem do Abacus AI
Explorando Base64ImageResponseSection
"""

import base64
import aiohttp
import asyncio
import logging
import os
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class AbacusImageTester:
    """Testador de análise de imagem do Abacus"""
    
    def __init__(self):
        self.api_key = os.getenv("ABACUS_API_KEY", "")
        # URL base descoberta para endpoints de visão
        self.base_url = "https://apps.abacus.ai/api/v0"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
    
    async def test_image_analysis_capability(self, image_data: bytes) -> Dict[str, Any]:
        """Testar se Abacus suporta análise de imagem"""
        
        results = {
            "vision_endpoints": await self._test_vision_endpoints(image_data),
            "classify_image": await self._test_classify_image(image_data),
            "describe_image": await self._test_describe_image(image_data),
            "get_objects": await self._test_get_objects_from_image(image_data),
            "base64_test": await self._test_base64_image_input(image_data),
            "multimodal_test": await self._test_multimodal_input(image_data),
            "available_models": await self._get_available_models()
        }
        
        return results
    
    async def _test_classify_image(self, image_data: bytes) -> Dict[str, Any]:
        """Testar endpoint /classifyImage"""
        try:
            image_b64 = base64.b64encode(image_data).decode()
            
            payload = {
                "image": image_b64
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/classifyImage",
                    headers=self.headers,
                    json=payload
                ) as response:
                    result = await response.text()
                    return {
                        "status": response.status,
                        "response": result,
                        "success": response.status == 200
                    }
        except Exception as e:
            return {"error": str(e), "success": False}
    
    async def _test_describe_image(self, image_data: bytes) -> Dict[str, Any]:
        """Testar endpoint /describeImage"""
        try:
            image_b64 = base64.b64encode(image_data).decode()
            
            payload = {
                "image": image_b64
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/describeImage",
                    headers=self.headers,
                    json=payload
                ) as response:
                    result = await response.text()
                    return {
                        "status": response.status,
                        "response": result,
                        "success": response.status == 200
                    }
        except Exception as e:
            return {"error": str(e), "success": False}
    
    async def _test_get_objects_from_image(self, image_data: bytes) -> Dict[str, Any]:
        """Testar endpoint /getObjectsFromImage"""
        try:
            image_b64 = base64.b64encode(image_data).decode()
            
            payload = {
                "image": image_b64
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.base_url}/getObjectsFromImage",
                    headers=self.headers,
                    json=payload
                ) as response:
                    result = await response.text()
                    return {
                        "status": response.status,
                        "response": result,
                        "success": response.status == 200
                    }
        except Exception as e:
            return {"error": str(e), "success": False}

    async def _test_base64_image_input(self, image_data: bytes) -> Dict[str, Any]:
        """Testar entrada de imagem em base64"""
        try:
            image_base64 = base64.b64encode(image_data).decode('utf-8')
            
            # Teste 1: Formato OpenAI-like com imagem
            payload_openai_style = {
                "model": "gpt-4-vision-preview",  # Tentar modelo de visão
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": "Analise esta imagem de imóvel e descreva suas características."
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{image_base64}"
                                }
                            }
                        ]
                    }
                ],
                "max_tokens": 300
            }
            
            result1 = await self._make_api_call("/chat/completions", payload_openai_style)
            
            # Teste 2: Formato alternativo
            payload_alt = {
                "model": "gpt-3.5-turbo",
                "messages": [
                    {
                        "role": "user", 
                        "content": f"Analise esta imagem em base64: data:image/jpeg;base64,{image_base64[:100]}..."
                    }
                ],
                "base64_image": image_base64,  # Campo customizado
                "image_analysis": True
            }
            
            result2 = await self._make_api_call("/chat/completions", payload_alt)
            
            return {
                "openai_style": result1,
                "alternative_format": result2,
                "image_size": len(image_data),
                "base64_size": len(image_base64)
            }
            
        except Exception as e:
            return {"error": str(e), "method": "base64_test"}
    
    async def _test_vision_endpoints(self, image_data: bytes) -> Dict[str, Any]:
        """Testar endpoints específicos de visão"""
        try:
            image_base64 = base64.b64encode(image_data).decode('utf-8')
            
            # Testar endpoints possíveis
            endpoints_to_test = [
                "/vision/analyze",
                "/image/analyze", 
                "/v1/vision/analyze",
                "/analyze/image",
                "/chat/vision",
                "/models/vision"
            ]
            
            results = {}
            
            for endpoint in endpoints_to_test:
                payload = {
                    "image": image_base64,
                    "prompt": "Analise esta imagem de imóvel",
                    "task": "property_analysis"
                }
                
                result = await self._make_api_call(endpoint, payload)
                results[endpoint] = result
            
            return results
            
        except Exception as e:
            return {"error": str(e), "method": "vision_endpoints"}
    
    async def _test_multimodal_input(self, image_data: bytes) -> Dict[str, Any]:
        """Testar entrada multimodal"""
        try:
            image_base64 = base64.b64encode(image_data).decode('utf-8')
            
            # Formato multimodal
            payload = {
                "model": "gpt-4",
                "input": {
                    "text": "Analise esta propriedade imobiliária",
                    "image": image_base64,
                    "format": "base64"
                },
                "task": "image_analysis",
                "response_format": "Base64ImageResponseSection"  # Campo específico mencionado
            }
            
            result = await self._make_api_call("/chat/completions", payload)
            
            return {
                "multimodal_result": result,
                "response_format_used": "Base64ImageResponseSection"
            }
            
        except Exception as e:
            return {"error": str(e), "method": "multimodal_test"}
    
    async def _get_available_models(self) -> Dict[str, Any]:
        """Listar modelos disponíveis"""
        try:
            # Testar endpoint de modelos
            result = await self._make_api_call("/models", {}, method="GET")
            return result
            
        except Exception as e:
            return {"error": str(e), "method": "models_list"}
    
    async def _make_api_call(self, endpoint: str, payload: Dict, method: str = "POST") -> Dict[str, Any]:
        """Fazer chamada para API do Abacus"""
        try:
            url = f"{self.base_url}{endpoint}"
            
            async with aiohttp.ClientSession() as session:
                if method == "GET":
                    async with session.get(url, headers=self.headers) as response:
                        return await self._process_response(response, endpoint)
                else:
                    async with session.post(url, headers=self.headers, json=payload) as response:
                        return await self._process_response(response, endpoint)
                        
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "endpoint": endpoint,
                "method": method
            }
    
    async def _process_response(self, response, endpoint: str) -> Dict[str, Any]:
        """Processar resposta da API"""
        try:
            status = response.status
            
            if status == 200:
                data = await response.json()
                return {
                    "success": True,
                    "status": status,
                    "data": data,
                    "endpoint": endpoint,
                    "supports_feature": True
                }
            else:
                error_text = await response.text()
                return {
                    "success": False,
                    "status": status,
                    "error": error_text,
                    "endpoint": endpoint,
                    "supports_feature": False
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": f"Response processing error: {str(e)}",
                "endpoint": endpoint
            }

# Função de teste principal
async def test_abacus_image_capabilities():
    """Função principal para testar capacidades de imagem"""
    print("🔍 Testando capacidades de análise de imagem do Abacus AI...")
    
    tester = AbacusImageTester()
    
    if not tester.api_key:
        print("❌ ABACUS_API_KEY não configurado!")
        return
    
    # Criar uma imagem de teste pequena (1x1 pixel)
    import io
    from PIL import Image
    
    # Criar imagem de teste
    test_image = Image.new('RGB', (1, 1), color='red')
    img_bytes = io.BytesIO()
    test_image.save(img_bytes, format='JPEG')
    image_data = img_bytes.getvalue()
    
    print(f"📷 Usando imagem de teste: {len(image_data)} bytes")
    
    # Executar testes
    results = await tester.test_image_analysis_capability(image_data)
    
    # Exibir resultados
    print("\n📊 RESULTADOS DOS TESTES:")
    print("=" * 50)
    
    for test_name, result in results.items():
        print(f"\n🧪 {test_name.upper()}:")
        
        if isinstance(result, dict):
            if result.get("success"):
                print(f"   ✅ SUCESSO!")
                if "data" in result:
                    print(f"   📄 Dados: {str(result['data'])[:100]}...")
            else:
                print(f"   ❌ Falhou: {result.get('error', 'Erro desconhecido')}")
                if result.get("status"):
                    print(f"   📋 Status: {result['status']}")
        else:
            print(f"   📄 Resultado: {str(result)[:200]}...")
    
    return results

if __name__ == "__main__":
    asyncio.run(test_abacus_image_capabilities())
