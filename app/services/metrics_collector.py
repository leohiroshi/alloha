"""
Sistema de Métricas para Monitorar Performance vs Concorrentes
Track: latência, conversão, qualidade, custos
"""

import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from dataclasses import dataclass, field
import logging
import json
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class MetricSnapshot:
    """Snapshot de métricas em um momento"""
    timestamp: datetime
    latency_ms: float
    success: bool
    model_used: str
    tokens_used: int
    lead_score: Optional[int] = None
    has_scheduling: bool = False
    urgency_detected: bool = False
    cost_usd: float = 0.0


class MetricsCollector:
    """Coleta e agrega métricas de produção"""
    
    def __init__(self):
        self.snapshots: List[MetricSnapshot] = []
        self.targets = {
            "latency_ms": 900,  # Lais: 2100ms, Meta: < 900ms
            "appointment_rate": 0.38,  # Lais: 19%, Meta: 38%
            "response_quality": 0.85  # Score de qualidade mínimo
        }
    
    def record_interaction(
        self,
        latency_ms: float,
        success: bool,
        model_used: str,
        tokens_used: int,
        lead_score: Optional[int] = None,
        has_scheduling: bool = False,
        urgency_detected: bool = False
    ):
        """Registra uma interação"""
        
        # Calcular custo (GPT-4o-mini: $0.15/1M input, $0.60/1M output)
        # Aproximação: 70% input, 30% output
        input_tokens = int(tokens_used * 0.7)
        output_tokens = int(tokens_used * 0.3)
        
        cost_usd = (input_tokens * 0.15 / 1_000_000) + (output_tokens * 0.60 / 1_000_000)
        
        snapshot = MetricSnapshot(
            timestamp=datetime.utcnow(),
            latency_ms=latency_ms,
            success=success,
            model_used=model_used,
            tokens_used=tokens_used,
            lead_score=lead_score,
            has_scheduling=has_scheduling,
            urgency_detected=urgency_detected,
            cost_usd=cost_usd
        )
        
        self.snapshots.append(snapshot)
        
        # Manter apenas últimas 10k interações (ou últimas 7 dias)
        cutoff = datetime.utcnow() - timedelta(days=7)
        self.snapshots = [s for s in self.snapshots if s.timestamp > cutoff][-10000:]
    
    def get_metrics(self, hours: int = 24) -> Dict:
        """Retorna métricas agregadas do período"""
        
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        recent = [s for s in self.snapshots if s.timestamp > cutoff]
        
        if not recent:
            return {"error": "No data available"}
        
        # Métricas de latência
        latencies = [s.latency_ms for s in recent if s.success]
        avg_latency = sum(latencies) / len(latencies) if latencies else 0
        p95_latency = sorted(latencies)[int(len(latencies) * 0.95)] if latencies else 0
        
        # Taxa de sucesso
        total = len(recent)
        successes = sum(1 for s in recent if s.success)
        success_rate = successes / total if total > 0 else 0
        
        # Taxa de agendamento (proxy para conversão)
        schedulings = sum(1 for s in recent if s.has_scheduling)
        appointment_rate = schedulings / total if total > 0 else 0
        
        # Detecção de urgência
        urgent = sum(1 for s in recent if s.urgency_detected)
        urgency_rate = urgent / total if total > 0 else 0
        
        # Lead quality
        scored_leads = [s for s in recent if s.lead_score is not None]
        avg_lead_score = sum(s.lead_score for s in scored_leads) / len(scored_leads) if scored_leads else 0
        
        # Custos
        total_cost = sum(s.cost_usd for s in recent)
        avg_cost_per_interaction = total_cost / total if total > 0 else 0
        
        # Comparação com targets
        latency_vs_target = (avg_latency / self.targets["latency_ms"]) * 100
        appointment_vs_target = (appointment_rate / self.targets["appointment_rate"]) * 100
        
        return {
            "period_hours": hours,
            "total_interactions": total,
            "success_rate": success_rate,
            
            "latency": {
                "avg_ms": round(avg_latency, 1),
                "p95_ms": round(p95_latency, 1),
                "target_ms": self.targets["latency_ms"],
                "vs_target": f"{latency_vs_target:.0f}%",
                "beats_lais": avg_latency < 2100  # Lais: 2.1s
            },
            
            "conversion": {
                "appointment_rate": round(appointment_rate, 3),
                "target_rate": self.targets["appointment_rate"],
                "vs_target": f"{appointment_vs_target:.0f}%",
                "beats_lais": appointment_rate > 0.19  # Lais: 19%
            },
            
            "quality": {
                "avg_lead_score": round(avg_lead_score, 2),
                "urgency_detection_rate": round(urgency_rate, 3)
            },
            
            "costs": {
                "total_usd": round(total_cost, 4),
                "avg_per_interaction_usd": round(avg_cost_per_interaction, 6),
                "projected_monthly_usd": round(avg_cost_per_interaction * 100000, 2)  # 100k msgs/mês
            },
            
            "competitive_advantage": {
                "latency_improvement": f"{((2100 - avg_latency) / 2100 * 100):.0f}% faster than Lais",
                "conversion_improvement": f"{((appointment_rate - 0.19) / 0.19 * 100):.0f}% better than Lais" if appointment_rate > 0.19 else "Below Lais"
            }
        }
    
    def export_metrics(self, filepath: str = "metrics_export.json"):
        """Exporta métricas para análise"""
        
        metrics_24h = self.get_metrics(hours=24)
        metrics_7d = self.get_metrics(hours=168)
        
        export_data = {
            "exported_at": datetime.utcnow().isoformat(),
            "last_24h": metrics_24h,
            "last_7d": metrics_7d,
            "raw_snapshots_count": len(self.snapshots)
        }
        
        output_path = Path("logs") / filepath
        output_path.parent.mkdir(exist_ok=True)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Metrics exported to {output_path}")
        return str(output_path)
    
    def print_dashboard(self):
        """Imprime dashboard de métricas"""
        
        metrics = self.get_metrics(hours=24)
        
        if "error" in metrics:
            print(f"\n⚠️  {metrics['error']}\n")
            return
        
        print("\n" + "="*80)
        print("📊 DASHBOARD DE MÉTRICAS - ÚLTIMAS 24H")
        print("="*80)
        
        print(f"\n📈 Performance:")
        print(f"   Total de interações: {metrics['total_interactions']}")
        print(f"   Taxa de sucesso: {metrics['success_rate']:.1%}")
        
        print(f"\n⚡ Latência:")
        print(f"   Média: {metrics['latency']['avg_ms']:.0f}ms")
        print(f"   P95: {metrics['latency']['p95_ms']:.0f}ms")
        print(f"   Target: {metrics['latency']['target_ms']}ms")
        print(f"   vs Target: {metrics['latency']['vs_target']}")
        
        if metrics['latency']['beats_lais']:
            print(f"   ✅ BATENDO LAIS! ({metrics['competitive_advantage']['latency_improvement']})")
        else:
            print(f"   ⚠️  Ainda não bateu Lais")
        
        print(f"\n🎯 Conversão:")
        print(f"   Taxa de agendamento: {metrics['conversion']['appointment_rate']:.1%}")
        print(f"   Target: {metrics['conversion']['target_rate']:.1%}")
        print(f"   vs Target: {metrics['conversion']['vs_target']}")
        
        if metrics['conversion']['beats_lais']:
            print(f"   ✅ BATENDO LAIS! ({metrics['competitive_advantage']['conversion_improvement']})")
        else:
            print(f"   ⚠️  Ainda não bateu Lais")
        
        print(f"\n💰 Custos:")
        print(f"   Total 24h: ${metrics['costs']['total_usd']:.4f}")
        print(f"   Média/interação: ${metrics['costs']['avg_per_interaction_usd']:.6f}")
        print(f"   Projeção mensal: ${metrics['costs']['projected_monthly_usd']:.2f}")
        
        print(f"\n📊 Qualidade:")
        print(f"   Lead score médio: {metrics['quality']['avg_lead_score']:.2f}/5")
        print(f"   Taxa de detecção de urgência: {metrics['quality']['urgency_detection_rate']:.1%}")
        
        print("\n" + "="*80 + "\n")


# Instância global
metrics_collector = MetricsCollector()
