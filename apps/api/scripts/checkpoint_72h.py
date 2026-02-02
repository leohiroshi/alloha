#!/usr/bin/env python3
"""
DEPRECATED CHECKPOINT SCRIPT (Firebase -> Supabase Migration Complete)

Este script original foi DESCONTINUADO pois dependia de Firestore/Firebase.
Toda a lógica foi distribuída entre serviços Supabase:
 - live_pricing_system (upsert + embeddings)
 - rag_pipeline (busca vetorial/híbrida)
 - dataset_living_loop (atualização incremental fine-tune)
 - voice_ptt_system (voz e preferências)
 - urgency_score_system (alertas de urgência)

Se precisar de um novo checkpoint, criar script novo 100% Supabase.
"""

from datetime import datetime

def main():
    print("[DEPRECATED] checkpoint_72h.py não é mais utilizado.")
    print("Data:", datetime.utcnow().isoformat())
    print("Consulte os serviços em app/services para fluxos ativos.")

if __name__ == "__main__":
    main()