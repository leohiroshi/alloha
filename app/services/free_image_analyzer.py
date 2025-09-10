"""
Analisador de Imagens GRATUITO para Imóveis
Usando análise de metadados e padrões visuais básicos
"""

import os
import logging
from PIL import Image, ImageStat
import io
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class FreePropertyImageAnalyzer:
    """Análise gratuita de imagens de imóveis"""
    
    def __init__(self):
        self.property_keywords = {
            'residential': ['casa', 'apartamento', 'residencia', 'moradia'],
            'commercial': ['loja', 'escritorio', 'comercial', 'salao'],
            'luxury': ['luxo', 'alto padrão', 'premium', 'sofisticado'],
            'basic': ['simples', 'basico', 'economico', 'funcional']
        }
    
    async def analyze_property_image_free(self, image_data: bytes, filename: str = "") -> Dict[str, Any]:
        """Análise gratuita de imagem de imóvel"""
        try:
            # Abrir imagem
            image = Image.open(io.BytesIO(image_data))
            
            # Análise básica
            analysis = {
                "tipo_analise": "Análise Gratuita Básica",
                "dimensoes": {
                    "largura": image.width,
                    "altura": image.height,
                    "proporcao": round(image.width / image.height, 2)
                },
                "formato": image.format,
                "tamanho_bytes": len(image_data),
                "qualidade_estimada": self._estimate_image_quality(image),
                "caracteristicas_visuais": self._analyze_visual_features(image),
                "sugestoes_imovel": self._suggest_property_type(image, filename),
                "recomendacoes": self._generate_recommendations(image),
                "confiabilidade": "Básica - Análise por padrões visuais"
            }
            
            return analysis
            
        except Exception as e:
            logger.error(f"Erro na análise gratuita: {str(e)}")
            return {"erro": str(e), "analise_disponivel": False}
    
    def _estimate_image_quality(self, image: Image.Image) -> Dict[str, Any]:
        """Estimar qualidade da imagem"""
        try:
            # Converter para RGB se necessário
            if image.mode != 'RGB':
                image = image.convert('RGB')
            
            # Calcular estatísticas
            stat = ImageStat.Stat(image)
            
            # Brilho médio
            brightness = sum(stat.mean) / len(stat.mean)
            
            # Contraste (desvio padrão)
            contrast = sum(stat.stddev) / len(stat.stddev)
            
            # Qualidade estimada
            quality_score = min(100, (brightness + contrast) / 5)
            
            return {
                "brilho": round(brightness, 2),
                "contraste": round(contrast, 2),
                "pontuacao_qualidade": round(quality_score, 1),
                "classificacao": self._classify_quality(quality_score)
            }
            
        except Exception as e:
            return {"erro": str(e)}
    
    def _classify_quality(self, score: float) -> str:
        """Classificar qualidade da imagem"""
        if score >= 80:
            return "Excelente para marketing"
        elif score >= 60:
            return "Boa qualidade"
        elif score >= 40:
            return "Qualidade média"
        else:
            return "Qualidade baixa - considere nova foto"
    
    def _analyze_visual_features(self, image: Image.Image) -> Dict[str, Any]:
        """Analisar características visuais básicas"""
        try:
            # Análise de cores dominantes
            colors = image.getcolors(maxcolors=256*256*256)
            if colors:
                # Cores mais comuns
                dominant_colors = sorted(colors, key=lambda x: x[0], reverse=True)[:5]
                
                color_analysis = {
                    "cores_dominantes": len(dominant_colors),
                    "variedade_cores": "Alta" if len(colors) > 1000 else "Média" if len(colors) > 500 else "Baixa"
                }
            else:
                color_analysis = {"erro": "Não foi possível analisar cores"}
            
            # Proporção da imagem
            aspect_ratio = image.width / image.height
            orientation = "Paisagem" if aspect_ratio > 1.3 else "Retrato" if aspect_ratio < 0.8 else "Quadrada"
            
            return {
                "orientacao": orientation,
                "proporcao": round(aspect_ratio, 2),
                "resolucao": "Alta" if image.width * image.height > 1000000 else "Média" if image.width * image.height > 300000 else "Baixa",
                "cores": color_analysis
            }
            
        except Exception as e:
            return {"erro": str(e)}
    
    def _suggest_property_type(self, image: Image.Image, filename: str) -> Dict[str, Any]:
        """Sugerir tipo de imóvel baseado em padrões"""
        suggestions = []
        confidence = "Baixa"
        
        # Análise baseada no nome do arquivo
        filename_lower = filename.lower()
        
        if any(word in filename_lower for word in ['apt', 'apartamento', 'ap']):
            suggestions.append("Apartamento")
            confidence = "Média"
        elif any(word in filename_lower for word in ['casa', 'residencia']):
            suggestions.append("Casa")
            confidence = "Média"
        elif any(word in filename_lower for word in ['comercial', 'loja', 'escritorio']):
            suggestions.append("Comercial")
            confidence = "Média"
        
        # Análise baseada na proporção
        aspect_ratio = image.width / image.height
        if aspect_ratio > 1.5:  # Muito horizontal
            suggestions.append("Possível foto externa ou panorâmica")
        elif aspect_ratio < 0.7:  # Muito vertical
            suggestions.append("Possível foto interna ou de fachada")
        
        # Análise baseada no tamanho
        total_pixels = image.width * image.height
        if total_pixels > 2000000:  # Imagem muito grande
            suggestions.append("Foto profissional - boa para marketing")
        
        return {
            "sugestoes": suggestions if suggestions else ["Tipo não identificado"],
            "confiabilidade": confidence,
            "recomendacao": "Adicione palavras-chave no nome do arquivo para melhor identificação"
        }
    
    def _generate_recommendations(self, image: Image.Image) -> list:
        """Gerar recomendações para melhoria"""
        recommendations = []
        
        # Verificar resolução
        total_pixels = image.width * image.height
        if total_pixels < 300000:
            recommendations.append("📱 Considere usar uma câmera com maior resolução")
        
        # Verificar proporção
        aspect_ratio = image.width / image.height
        if aspect_ratio > 2.0 or aspect_ratio < 0.5:
            recommendations.append("📐 Proporção muito extrema - considere enquadramento mais equilibrado")
        
        # Verificar tamanho do arquivo
        if hasattr(image, 'size') and image.size < 100000:
            recommendations.append("💾 Arquivo muito pequeno - pode comprometer a qualidade")
        
        # Recomendações gerais
        recommendations.extend([
            "💡 Para melhor análise, tire fotos em boa iluminação",
            "🏠 Inclua diferentes ângulos do imóvel",
            "📝 Nomeie os arquivos com descrições (ex: 'casa_3quartos_sala.jpg')"
        ])
        
        return recommendations

# Instância global
free_analyzer = FreePropertyImageAnalyzer()
