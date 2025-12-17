#!/usr/bin/env python3
# ============================================================================
# MODELO DE OTIMIZAÇÃO DE MIX - DO ZERO
# ============================================================================
# Baseado em dados unificados:
# 1. Agrega dados por SKU (soma volumes por diretoria/mês)
# 2. Agrupa por TIPO (Item|Embalagem = Embalagem|Tamanho)
# 3. Otimiza distribuição dentro de cada TIPO para maximizar lucro
# 4. Respeita capacidade mensal do TIPO
# 5. Não excede demanda do mercado
# ============================================================================

import os
import numpy as np
import pandas as pd
from scipy.optimize import minimize
import warnings
warnings.filterwarnings('ignore')

# ============================================================================
# CARREGAMENTO E PREPARAÇÃO DE DADOS
# ============================================================================
def load_and_prepare_unified_data(data_file="data_unified.csv", filter_months=None):
    """
    Carrega e prepara dados unificados.
    
    Args:
        data_file: Caminho do arquivo CSV
        filter_months: Lista de meses (datetime) para filtrar. Se None, usa todos os meses.
    """
    print("=" * 80)
    print("CARREGAMENTO E PREPARAÇÃO DE DADOS UNIFICADOS")
    print("=" * 80)
    
    # Carregar dados unificados
    print(f"\n[1] Carregando dados unificados de: {data_file}")
    if not os.path.exists(data_file):
        raise FileNotFoundError(f"Arquivo não encontrado: {data_file}")
    
    df = pd.read_csv(data_file, decimal=',', encoding='utf-8')
    print(f"  ✓ Carregado: {len(df)} linhas, {len(df.columns)} colunas")
    
    # IMPORTANTE: Filtrar por mês ANTES de agregar
    # O arquivo base tem uma linha por SKU por mês (depara_mess)
    if 'depara_mess' in df.columns:
        # Converter para datetime se necessário
        df['depara_mess'] = pd.to_datetime(df['depara_mess'], errors='coerce')
        meses_unicos = df['depara_mess'].dropna().unique()
        
        if filter_months is not None and len(filter_months) > 0:
            # Aplicar filtro de meses fornecido
            filter_months_dt = pd.to_datetime(filter_months)
            # Normalizar para primeiro dia do mês para comparação
            filter_months_normalized = [pd.Timestamp(m).replace(day=1) for m in filter_months_dt]
            df['depara_mess_normalized'] = df['depara_mess'].apply(
                lambda x: pd.Timestamp(x).replace(day=1) if pd.notna(x) else pd.NaT
            )
            mask_mes = df['depara_mess_normalized'].isin(filter_months_normalized)
            n_antes = len(df)
            df = df[mask_mes].copy()
            df = df.drop(columns=['depara_mess_normalized'], errors='ignore')
            print(f"  ✓ Filtrado por mês: {n_antes} -> {len(df)} linhas")
            print(f"  Meses filtrados: {[m.strftime('%Y-%m') for m in filter_months_dt]}")
        elif len(meses_unicos) > 1:
            # Se não há filtro mas há múltiplos meses, usar todos (agregar por mês também)
            print(f"  ⚠ Múltiplos meses encontrados: {len(meses_unicos)}")
            print(f"  ⚠ Usando TODOS os meses (agregando por mês)")
        elif len(meses_unicos) == 1:
            print(f"  ✓ Usando mês: {meses_unicos[0]}")
    
    # Agregar por SKU (somar volumes de diferentes diretorias/territórios)
    print(f"\n[2] Agregando dados por SKU...")
    print(f"  SKUs únicos antes: {df['chave_sku'].nunique()}")
    print(f"  Linhas antes: {len(df)}")
    
    # Colunas para agregação
    # Se há múltiplos meses, agregar por mês também. Se há um mês, volumes diferentes são de diretorias/territórios diferentes
    # Precisamos somar volumes de diferentes diretorias/territórios (e meses se houver múltiplos)
    agg_dict = {
        'volume_projetado': 'sum',  # Soma volumes de diferentes diretorias/territórios/meses
        'base_margem_variavel_unit': 'mean',  # Média da margem unitária
        'base_preco_liquido_unit': 'mean',
        'elasticidade': 'mean',
        'capacidade_min': 'first',  # Capacidade é por TIPO, não por SKU
        'capacidade_max': 'first',
    }
    
    # Manter colunas de identificação
    id_cols = ['chave_sku', 'brand', 'size', 'tipo_consumo', 'returnability', 'package', 'tipo']
    
    # Se há múltiplos meses e não foi filtrado, incluir depara_mess na agregação
    # Mas se foi filtrado, não precisa (já está filtrado)
    if filter_months is None and 'depara_mess' in df.columns:
        meses_unicos = df['depara_mess'].dropna().unique()
        if len(meses_unicos) > 1:
            # Se há múltiplos meses sem filtro, manter depara_mess para agregação
            # Mas na verdade, se não foi filtrado, devemos agregar todos os meses juntos
            print(f"  ⚠ Agregando volumes de {len(meses_unicos)} meses diferentes")
    id_cols = [col for col in id_cols if col in df.columns]
    
    # Adicionar grupo_capacidade se existir
    if 'grupo_capacidade' in df.columns:
        id_cols.append('grupo_capacidade')
    
    # Agregar
    df_agg = df.groupby(id_cols, as_index=False).agg(agg_dict).reset_index(drop=True)
    
    print(f"  ✓ Agregado: {len(df_agg)} SKUs únicos")
    print(f"  TIPOs únicos: {df_agg['tipo'].nunique()}")
    
    # Verificar dados
    print(f"\n[3] Verificando dados...")
    print(f"  SKUs com volume_projetado > 0: {(df_agg['volume_projetado'] > 0).sum()}")
    print(f"  SKUs com margem > 0: {(df_agg['base_margem_variavel_unit'] > 0).sum()}")
    print(f"  SKUs com capacidade definida: {df_agg['capacidade_max'].notna().sum()}")
    
    # Estatísticas por TIPO
    print(f"\n[4] Estatísticas por TIPO:")
    tipo_stats = df_agg.groupby('tipo').agg({
        'chave_sku': 'count',
        'volume_projetado': 'sum',
        'base_margem_variavel_unit': 'mean',
        'capacidade_max': 'first',
        'capacidade_min': 'first'
    }).reset_index()
    tipo_stats.columns = ['TIPO', 'N_SKUs', 'Volume_Total', 'Margem_Media', 'Cap_Max', 'Cap_Min']
    
    for _, row in tipo_stats.iterrows():
        print(f"  {row['TIPO']}: {row['N_SKUs']} SKUs, Volume: {row['Volume_Total']:,.0f} UC, "
              f"Margem: R$ {row['Margem_Media']:.2f}/UC, "
              f"Cap: {row['Cap_Min']:,.0f}-{row['Cap_Max']:,.0f} UC" if pd.notna(row['Cap_Max']) else f"Cap: Inf")
    
    return df_agg

# ============================================================================
# MODELOS DE OTIMIZAÇÃO SEPARADOS
# ============================================================================

def optimize_single_tipo_group(df_grupo, grupo, cap_min, cap_max, demandas, lucros_unit, indices_tipo):
    """
    Otimiza grupos com APENAS 1 TIPO.
    Modelo mais simples: apenas verificar capacidade e demanda.
    """
    n_tipos = len(df_grupo)
    if n_tipos != 1:
        return None
    
    demanda = demandas[0]
    lucro_unit = lucros_unit[0]
    idx_tipo = indices_tipo[0]
    
    # Para 1 TIPO: simplesmente usar o mínimo entre demanda e capacidade máxima
    # E garantir que seja >= capacidade mínima
    volume_otimizado = min(demanda, cap_max) if cap_max < float('inf') else demanda
    
    # Se volume < cap_min e demanda >= cap_min, usar cap_min
    if cap_min > 0 and volume_otimizado < cap_min and demanda >= cap_min:
        volume_otimizado = min(cap_min, cap_max) if cap_max < float('inf') else cap_min
    
    # Não pode exceder demanda
    volume_otimizado = min(volume_otimizado, demanda)
    
    lucro_total = volume_otimizado * lucro_unit
    atendimento_pct = (volume_otimizado / demanda * 100) if demanda > 0 else 0
    
    # Status
    if volume_otimizado > cap_max and cap_max < float('inf'):
        status_grupo = 'Acima Máximo'
    elif volume_otimizado < cap_min and cap_min > 0:
        status_grupo = 'Abaixo Mínimo'
    else:
        status_grupo = 'OK'
    
    return {
        'volumes_otimizados': np.array([volume_otimizado]),
        'lucro_total': lucro_total,
        'atendimento_pct': atendimento_pct,
        'status_grupo': status_grupo,
        'volume_total_final': volume_otimizado
    }

def optimize_multi_tipo_group(df_grupo, grupo, cap_min, cap_max, demandas, lucros_unit, indices_tipo):
    """
    Otimiza grupos com MÚLTIPLOS TIPOs (2+).
    Usa otimização SLSQP para distribuir capacidade entre TIPOs.
    """
    n_tipos = len(df_grupo)
    if n_tipos < 2:
        return None
    
    demanda_total = demandas.sum()
    
    # Função objetivo: maximizar lucro total (minimizar negativo)
    def objetivo(x):
        """
        Função objetivo: MAXIMIZAR lucro total (minimizar negativo do lucro).
        Prioriza TIPOs mais rentáveis quando há capacidade limitada.
        """
        # Lucro total = soma de (lucro_unitário * volume) para cada TIPO
        lucro_total = -np.sum(lucros_unit * x)  # Negativo porque minimize() minimiza
        
        # Penalidades (valores grandes para garantir que violações sejam evitadas)
        volume_total = np.sum(x)
        
        # Penalidade por exceder capacidade máxima (CRÍTICO)
        if volume_total > cap_max and cap_max < float('inf'):
            lucro_total += 1e10 * (volume_total - cap_max)
        
        # Penalidade por não atingir capacidade mínima (se viável)
        if volume_total < cap_min and cap_min > 0 and cap_min < cap_max:
            lucro_total += 1e6 * (cap_min - volume_total)
        
        # Penalidade por exceder demanda individual (CRÍTICO)
        excesso_demanda = np.sum(np.maximum(0, x - demandas))
        if excesso_demanda > 0:
            lucro_total += 1e8 * excesso_demanda
        
        # Penalidade por volumes negativos (CRÍTICO)
        volumes_negativos = np.sum(np.maximum(0, -x))
        if volumes_negativos > 0:
            lucro_total += 1e10 * volumes_negativos
        
        # BONUS: Priorizar TIPOs mais rentáveis quando capacidade é limitada
        # Adicionar um pequeno bonus proporcional ao lucro unitário para garantir priorização
        # Isso ajuda o otimizador a preferir alocar para TIPOs mais rentáveis
        if cap_max < float('inf') and demanda_total > cap_max:
            # Quando há restrição de capacidade, dar bonus maior para TIPOs mais rentáveis
            lucros_normalizados = (lucros_unit - lucros_unit.min()) / (lucros_unit.max() - lucros_unit.min() + 1e-10)
            bonus_priorizacao = -1e3 * np.sum(lucros_normalizados * x)  # Negativo porque estamos minimizando
            lucro_total += bonus_priorizacao
        
        return lucro_total
    
    # Restrições
    constraints = []
    
    # Restrição: volume total <= capacidade máxima
    if cap_max < float('inf'):
        constraints.append({
            'type': 'ineq',
            'fun': lambda x: cap_max - np.sum(x)
        })
    
    # Bounds: apenas limitar pela demanda individual (NÃO por cap_max!)
    bounds = [(0.0, dem) for dem in demandas]
    
    # Restrição: volume total >= capacidade mínima (se viável)
    soma_bounds_max = sum(b[1] for b in bounds)
    if (cap_min > 0 and 
        cap_min < cap_max and
        soma_bounds_max >= cap_min):
        constraints.append({
            'type': 'ineq',
            'fun': lambda x: np.sum(x) - cap_min
        })
    
    # Ponto inicial: PRIORIZAR TIPOs mais lucrativos
    # Ordenar por lucro unitário (maior primeiro) para garantir priorização
    x0 = np.zeros(n_tipos)
    idxs_ordenados = np.argsort(lucros_unit)[::-1]  # Ordem decrescente de lucro
    
    if cap_max < float('inf') and demanda_total > cap_max:
        # Demanda excede capacidade: alocar para os MAIS RENTÁVEIS primeiro
        print(f"      📊 Capacidade limitada. Priorizando TIPOs por rentabilidade:")
        capacidade_restante = cap_max
        for idx in idxs_ordenados:
            if capacidade_restante <= 0:
                break
            alocacao = min(demandas[idx], capacidade_restante)
            x0[idx] = alocacao
            capacidade_restante -= alocacao
            if alocacao > 0:
                tipo_nome = df_grupo.iloc[idx]['tipo'] if idx < len(df_grupo) else f"TIPO_{idx}"
                print(f"        {tipo_nome}: {alocacao:,.0f} UC (lucro: R$ {lucros_unit[idx]:,.2f}/UC)")
    else:
        # Se cabe tudo, usar demanda completa
        x0 = demandas.copy()
        print(f"      ✓ Capacidade suficiente para atender toda demanda")
    
    # Verificar viabilidade
    soma_bounds_max = sum(b[1] for b in bounds)
    viável = True
    
    if cap_max < float('inf'):
        if cap_min > 0 and soma_bounds_max < cap_min:
            viável = False
        elif cap_min > cap_max:
            viável = False
    
    # Otimizar
    try:
        if viável:
            from scipy.optimize import minimize
            result = minimize(
                objetivo,
                x0,
                method='SLSQP',
                bounds=bounds,
                constraints=constraints,
                options={'maxiter': 1000, 'ftol': 1e-6, 'disp': False}
            )
        else:
            result = type('obj', (object,), {'success': False, 'message': 'Problema inviável', 'x': x0})()
        
        if result.success:
            volumes_otimizados = np.maximum(0, result.x)
            # GARANTIR: volumes nunca excedem demandas individuais
            volumes_otimizados = np.minimum(volumes_otimizados, demandas)
            
            # Validação adicional: verificar se algum volume ainda excede demanda
            excessos = volumes_otimizados > demandas
            if excessos.any():
                print(f"      ⚠️ [WARNING] Alguns volumes otimizados excedem demanda após np.minimum. Corrigindo...")
                volumes_otimizados = np.minimum(volumes_otimizados, demandas)
            
            # Ajustar se exceder capacidade total
            volume_total = volumes_otimizados.sum()
            if volume_total > cap_max and cap_max < float('inf'):
                print(f"      ⚠️ [WARNING] Volume total ({volume_total:,.0f}) excede capacidade ({cap_max:,.0f}). Redistribuindo...")
                # PRIORIZAR: Redistribuir capacidade para os TIPOs MAIS RENTÁVEIS primeiro
                # Ordenar por lucro unitário (maior primeiro)
                idxs_ordenados = np.argsort(lucros_unit)[::-1]  # Ordem decrescente de lucro
                print(f"      📊 Priorizando TIPOs por rentabilidade:")
                for i, idx in enumerate(idxs_ordenados):
                    tipo_nome = df_grupo.iloc[idx]['tipo'] if idx < len(df_grupo) else f"TIPO_{idx}"
                    print(f"        {i+1}. {tipo_nome}: R$ {lucros_unit[idx]:,.2f}/UC")
                
                volumes_otimizados = np.zeros(n_tipos)
                capacidade_restante = cap_max
                for idx in idxs_ordenados:
                    if capacidade_restante <= 0:
                        break
                    alocacao = min(demandas[idx], capacidade_restante)
                    volumes_otimizados[idx] = alocacao
                    capacidade_restante -= alocacao
                    if alocacao > 0:
                        print(f"        ✓ Alocado {alocacao:,.0f} UC para TIPO {idx} (lucro: R$ {lucros_unit[idx]:,.2f}/UC)")
                volume_total = volumes_otimizados.sum()
                print(f"      ✓ Volume após redistribuição: {volume_total:,.0f} UC (dentro da capacidade)")
            
            # GARANTIR: volume_total_final nunca excede cap_max
            volume_total_final = volumes_otimizados.sum()
            if volume_total_final > cap_max and cap_max < float('inf'):
                print(f"      ⚠️ [WARNING] Volume total ({volume_total_final:,.0f}) ainda excede capacidade ({cap_max:,.0f}) após redistribuição")
                # Limitar ao máximo da capacidade
                fator_limitacao = cap_max / volume_total_final
                volumes_otimizados = volumes_otimizados * fator_limitacao
                # Garantir que não excede demandas individuais
                volumes_otimizados = np.minimum(volumes_otimizados, demandas)
                volume_total_final = volumes_otimizados.sum()
                print(f"      ✓ Volume final após limitação: {volume_total_final:,.0f} UC")
            
            lucro_total = np.sum(lucros_unit * volumes_otimizados)
            atendimento_pct = (volume_total_final / demanda_total * 100) if demanda_total > 0 else 0
            
            # Status
            if volume_total_final > cap_max and cap_max < float('inf'):
                status_grupo = 'Acima Máximo'
            elif volume_total_final < cap_min and cap_min > 0:
                status_grupo = 'Abaixo Mínimo'
            else:
                status_grupo = 'OK'
            
            return {
                'volumes_otimizados': volumes_otimizados,
                'lucro_total': lucro_total,
                'atendimento_pct': atendimento_pct,
                'status_grupo': status_grupo,
                'volume_total_final': volume_total_final
            }
        else:
            # Fallback: PRIORIZAR TIPOs mais rentáveis
            print(f"      ⚠️ Otimização falhou. Usando fallback: priorizando TIPOs mais rentáveis...")
            idxs_ordenados = np.argsort(lucros_unit)[::-1]  # Ordem decrescente de lucro
            volumes_fallback = np.zeros(n_tipos)
            capacidade_restante = cap_max if cap_max < float('inf') else demanda_total
            
            print(f"      📊 Alocando capacidade por ordem de rentabilidade:")
            for idx in idxs_ordenados:
                if capacidade_restante <= 0:
                    break
                alocacao = min(demandas[idx], capacidade_restante)
                volumes_fallback[idx] = alocacao
                capacidade_restante -= alocacao
                if alocacao > 0:
                    tipo_nome = df_grupo.iloc[idx]['tipo'] if idx < len(df_grupo) else f"TIPO_{idx}"
                    print(f"        {tipo_nome}: {alocacao:,.0f} UC (lucro: R$ {lucros_unit[idx]:,.2f}/UC)")
            
            volume_total_final = volumes_fallback.sum()
            # GARANTIR: volume_total_final nunca excede cap_max no fallback também
            if volume_total_final > cap_max and cap_max < float('inf'):
                fator_limitacao = cap_max / volume_total_final
                volumes_fallback = volumes_fallback * fator_limitacao
                volumes_fallback = np.minimum(volumes_fallback, demandas)
                volume_total_final = volumes_fallback.sum()
            
            lucro_total = np.sum(lucros_unit * volumes_fallback)
            atendimento_pct = (volume_total_final / demanda_total * 100) if demanda_total > 0 else 0
            
            status_grupo = 'OK'
            if volume_total_final > cap_max and cap_max < float('inf'):
                status_grupo = 'Acima Máximo'
            elif volume_total_final < cap_min and cap_min > 0:
                status_grupo = 'Abaixo Mínimo'
            
            return {
                'volumes_otimizados': volumes_fallback,
                'lucro_total': lucro_total,
                'atendimento_pct': atendimento_pct,
                'status_grupo': status_grupo,
                'volume_total_final': volume_total_final
            }
    except Exception as e:
        print(f"      ⚠️ Erro na otimização: {e}")
        # Fallback: PRIORIZAR TIPOs mais rentáveis
        print(f"      📊 Usando fallback: priorizando TIPOs mais rentáveis...")
        idxs_ordenados = np.argsort(lucros_unit)[::-1]  # Ordem decrescente de lucro
        volumes_fallback = np.zeros(n_tipos)
        capacidade_restante = cap_max if cap_max < float('inf') else demanda_total
        
        print(f"      📊 Alocando capacidade por ordem de rentabilidade:")
        for idx in idxs_ordenados:
            if capacidade_restante <= 0:
                break
            alocacao = min(demandas[idx], capacidade_restante)
            volumes_fallback[idx] = alocacao
            capacidade_restante -= alocacao
            if alocacao > 0:
                tipo_nome = df_grupo.iloc[idx]['tipo'] if idx < len(df_grupo) else f"TIPO_{idx}"
                print(f"        {tipo_nome}: {alocacao:,.0f} UC (lucro: R$ {lucros_unit[idx]:,.2f}/UC)")
        
        volume_total_final = volumes_fallback.sum()
        # GARANTIR: volume_total_final nunca excede cap_max no exception também
        if volume_total_final > cap_max and cap_max < float('inf'):
            fator_limitacao = cap_max / volume_total_final
            volumes_fallback = volumes_fallback * fator_limitacao
            volumes_fallback = np.minimum(volumes_fallback, demandas)
            volume_total_final = volumes_fallback.sum()
        
        lucro_total = np.sum(lucros_unit * volumes_fallback)
        atendimento_pct = (volume_total_final / demanda_total * 100) if demanda_total > 0 else 0
        
        return {
            'volumes_otimizados': volumes_fallback,
            'lucro_total': lucro_total,
            'atendimento_pct': atendimento_pct,
            'status_grupo': 'OK',
            'volume_total_final': volume_total_final
        }

# ============================================================================
# OTIMIZAÇÃO POR TIPO (FUNÇÃO PRINCIPAL)
# ============================================================================
def optimize_by_tipo(df_work):
    """
    Otimiza mix de produção por GRUPO DE CAPACIDADE.
    
    IMPORTANTE: Agrega dados por TIPO dentro de cada GRUPO_CAPACIDADE antes de otimizar.
    A capacidade é compartilhada por grupo, mas as demandas são por TIPO.
    Ex: Pet|1.0 e Pet|1.5 compartilham capacidade Pet|1-1.5L
    
    Estratégia:
    1. Agregar por TIPO dentro de GRUPO_CAPACIDADE (soma demandas de SKUs do mesmo tipo)
    2. Para cada grupo, otimiza distribuição da capacidade compartilhada entre TIPOs
    3. Objetivo: Maximizar lucro total
    4. Restrições: Capacidade mensal compartilhada e demanda do mercado por TIPO
    """
    print("\n" + "=" * 80)
    print("OTIMIZAÇÃO POR GRUPO DE CAPACIDADE (Item|Embalagem)")
    print("=" * 80)
    
    # IMPORTANTE: Primeiro agregar por TIPO dentro de GRUPO_CAPACIDADE
    # NOTA: O filtro de mês já deve ter sido aplicado antes de chamar esta função
    # Não aplicar filtro automático aqui para respeitar o filtro do usuário
    if 'depara_mess' in df_work.columns:
        meses_unicos = df_work['depara_mess'].dropna().unique()
        if len(meses_unicos) > 1:
            print(f"[INFO] Múltiplos meses encontrados nos dados: {len(meses_unicos)} meses")
            print(f"[INFO] Usando todos os meses filtrados (não aplicando filtro automático)")
            # Não filtrar automaticamente - usar todos os meses que já foram filtrados
        elif len(meses_unicos) == 1:
            print(f"[INFO] Usando mês: {meses_unicos[0]}")
        else:
            print(f"[WARNING] Nenhum mês encontrado na coluna depara_mess")
    
    # FILTRAR: Remover linhas sem TIPO válido ANTES de agregar
    if 'tipo' in df_work.columns:
        mask_tipo_valido = (
            df_work['tipo'].notna() & 
            (df_work['tipo'].astype(str).str.strip() != '') &
            (df_work['tipo'].astype(str).str.strip() != 'nan')
        )
        n_antes = len(df_work)
        df_work = df_work[mask_tipo_valido].copy()
        n_depois = len(df_work)
        if n_antes > n_depois:
            print(f"[INFO] Removidas {n_antes - n_depois} linhas sem TIPO válido (antes: {n_antes}, depois: {n_depois})")
    
    # Agregar por TIPO dentro de cada GRUPO_CAPACIDADE
    if 'grupo_capacidade' in df_work.columns and df_work['grupo_capacidade'].notna().any():
        coluna_grupo = 'grupo_capacidade'
        print(f"\n[INFO] Agregando por TIPO dentro de GRUPO_CAPACIDADE...")
        
        # Agregar por tipo dentro do grupo
        df_work_agg = df_work.groupby(['grupo_capacidade', 'tipo']).agg({
            'volume_projetado': 'sum',  # Soma demanda de todos os SKUs do mesmo tipo
            'elasticidade': 'mean',
            'base_margem_variavel_unit': 'mean',  # Média da margem unitária do tipo
            'base_preco_liquido_unit': 'mean',
            'capacidade_min': 'first',  # Capacidade é por grupo, não por tipo
            'capacidade_max': 'first',
            'chave_sku': 'first',  # Manter uma chave_sku para referência
            'brand': lambda x: ', '.join(x.unique()[:3]) if len(x.unique()) > 0 else '',
            'package': 'first',
            'returnability': 'first'
        }).reset_index()
        
        print(f"[INFO] Agregado: {len(df_work_agg)} TIPOs únicos em {df_work_agg['grupo_capacidade'].nunique()} grupos")
    else:
        coluna_grupo = 'tipo'
        print(f"\n[INFO] Usando 'tipo' para agrupamento (fallback - sem grupo_capacidade)")
        df_work_agg = df_work.copy()
    
    # Preparar dados
    df_result = df_work_agg.copy()
    
    # Garantir que todas as linhas têm tipo válido (filtro adicional de segurança)
    if 'tipo' in df_result.columns:
        mask_tipo_valido = (
            df_result['tipo'].notna() & 
            (df_result['tipo'].astype(str).str.strip() != '') &
            (df_result['tipo'].astype(str).str.strip() != 'nan')
        )
        df_result = df_result[mask_tipo_valido].copy()
        print(f"[INFO] df_result após filtro de TIPO: {len(df_result)} linhas")
    
    df_result['volume_otimizado'] = 0.0
    df_result['lucro_otimizado'] = 0.0  # Adicionar coluna de lucro otimizado
    df_result['margem_total_otimizada'] = 0.0  # Adicionar coluna esperada pelo dashboard
    df_result['atendimento_pct'] = 0.0
    df_result['status_capacidade'] = 'OK'
    df_result['dentro_capacidade'] = True
    
    # Agrupar por grupo de capacidade
    grupos_unicos = df_result[coluna_grupo].dropna().unique()
    print(f"[INFO] {len(grupos_unicos)} grupos únicos encontrados")
    
    resultados_por_tipo = {}
    
    for grupo in grupos_unicos:
        df_grupo = df_work[df_work[coluna_grupo] == grupo].copy()
        
        if df_grupo.empty:
            continue
        
        n_tipos = len(df_grupo)
        print(f"\n  GRUPO: {grupo} ({n_tipos} TIPOs)")
        
        # Mostrar TIPOs dentro do grupo
        if 'tipo' in df_grupo.columns:
            tipos_no_grupo = df_grupo['tipo'].unique()
            print(f"    TIPOs: {', '.join(tipos_no_grupo)}")
        
        # Dados do GRUPO (agora por TIPO, não por SKU)
        demandas = df_grupo['volume_projetado'].fillna(0).values
        lucros_unit = df_grupo['base_margem_variavel_unit'].fillna(0).values
        indices_tipo = df_grupo.index.tolist()
        
        # Capacidade do GRUPO (compartilhada entre todos os SKUs do grupo)
        cap_min = df_grupo['capacidade_min'].iloc[0] if df_grupo['capacidade_min'].notna().any() else 0
        cap_max = df_grupo['capacidade_max'].iloc[0] if df_grupo['capacidade_max'].notna().any() else float('inf')
        demanda_total = demandas.sum()
        
        print(f"    Demanda total: {demanda_total:,.0f} UC")
        print(f"    Capacidade: {cap_min:,.0f} - {cap_max:,.0f} UC" if cap_max < float('inf') else f"    Capacidade: {cap_min:,.0f} - Inf UC")
        print(f"    Lucro médio: R$ {lucros_unit.mean():,.2f}/UC")
        print(f"    Lucro por TIPO:")
        for i, idx in enumerate(df_grupo.index):
            tipo_nome = df_grupo.loc[idx, 'tipo']
            lucro = lucros_unit[i]
            demanda = demandas[i]
            print(f"      - {tipo_nome}: R$ {lucro:,.2f}/UC (demanda: {demanda:,.0f} UC)")
        
        # ESCOLHER MODELO BASEADO NO NÚMERO DE TIPOs
        if n_tipos == 1:
            print(f"    📌 Usando modelo SIMPLES (1 TIPO)")
            resultado = optimize_single_tipo_group(
                df_grupo, grupo, cap_min, cap_max, demandas, lucros_unit, indices_tipo
            )
        else:
            print(f"    📌 Usando modelo MULTI-TIPO ({n_tipos} TIPOs)")
            resultado = optimize_multi_tipo_group(
                df_grupo, grupo, cap_min, cap_max, demandas, lucros_unit, indices_tipo
            )
        
        if resultado is None:
            print(f"    ✗ Erro: Não foi possível otimizar")
            continue
        
        # Extrair resultados
        volumes_otimizados = resultado['volumes_otimizados']
        lucro_total = resultado['lucro_total']
        atendimento_pct = resultado['atendimento_pct']
        status_grupo = resultado['status_grupo']
        volume_total_final = resultado['volume_total_final']
        
        # Atualizar resultado POR TIPO (não por grupo)
        for i, idx in enumerate(indices_tipo):
            # GARANTIR: volume otimizado nunca excede demanda individual
            volume_final = min(volumes_otimizados[i], demandas[i])
            df_result.at[idx, 'volume_otimizado'] = volume_final
            lucro_otimizado = lucros_unit[i] * volume_final
            df_result.at[idx, 'lucro_otimizado'] = lucro_otimizado
            df_result.at[idx, 'margem_total_otimizada'] = lucro_otimizado  # Mesmo valor (margem = lucro)
            df_result.at[idx, 'atendimento_pct'] = (volume_final / demandas[i] * 100) if demandas[i] > 0 else 0
            df_result.at[idx, 'status_capacidade'] = status_grupo
            
            # Log se houve ajuste
            if volumes_otimizados[i] > demandas[i]:
                print(f"      ⚠️ Ajuste: {df_grupo.loc[idx, 'tipo']} - volume otimizado ({volumes_otimizados[i]:,.0f}) > demanda ({demandas[i]:,.0f}), limitado a {volume_final:,.0f}")
        
        resultados_por_tipo[grupo] = {
            'volume_total': volume_total_final,
            'demanda_total': demanda_total,
            'lucro_total': lucro_total,
            'atendimento_pct': atendimento_pct,
            'n_tipos': n_tipos,
            'status': status_grupo
        }
        
        print(f"    ✓ Otimizado: {volume_total_final:,.0f} UC, Lucro: R$ {lucro_total:,.2f}, Status: {status_grupo}")
        
        # Mostrar detalhamento por TIPO
        print(f"    📊 Detalhamento por TIPO:")
        for i, idx in enumerate(indices_tipo):
            tipo_nome = df_grupo.loc[idx, 'tipo']
            print(f"      - {tipo_nome}: {volumes_otimizados[i]:,.0f} UC "
                  f"(demanda: {demandas[i]:,.0f}, lucro: R$ {lucros_unit[i] * volumes_otimizados[i]:,.2f})")
        
        # Fim do processamento deste grupo - continuar para o próximo
    
    # VALIDAÇÃO FINAL CRÍTICA: Garantir que volume_otimizado nunca excede volume_projetado
    print("\n[5] Validando volumes otimizados...")
    if 'volume_otimizado' in df_result.columns and 'volume_projetado' in df_result.columns:
        mask_excesso = df_result['volume_otimizado'] > df_result['volume_projetado']
        n_excessos = mask_excesso.sum()
        if n_excessos > 0:
            print(f"  ⚠️ [WARNING] {n_excessos} TIPOs com volume_otimizado > volume_projetado. Corrigindo...")
            df_result.loc[mask_excesso, 'volume_otimizado'] = df_result.loc[mask_excesso, 'volume_projetado']
            # Recalcular lucro e margem para os ajustados
            mask_excesso_idx = df_result[mask_excesso].index
            for idx in mask_excesso_idx:
                if 'base_margem_variavel_unit' in df_result.columns:
                    df_result.at[idx, 'lucro_otimizado'] = df_result.at[idx, 'volume_otimizado'] * df_result.at[idx, 'base_margem_variavel_unit']
                    df_result.at[idx, 'margem_total_otimizada'] = df_result.at[idx, 'lucro_otimizado']
                if 'volume_projetado' in df_result.columns and df_result.at[idx, 'volume_projetado'] > 0:
                    df_result.at[idx, 'atendimento_pct'] = (df_result.at[idx, 'volume_otimizado'] / df_result.at[idx, 'volume_projetado']) * 100
        else:
            print(f"  ✓ Todos os volumes otimizados estão dentro da demanda")
    
    # Calcular % de uso da capacidade por grupo
    print("\n[6] Calculando % de uso da capacidade...")
    df_result['uso_capacidade_pct'] = 0.0
    
    for grupo in grupos_unicos:
        mask_grupo = df_result[coluna_grupo] == grupo
        df_grupo = df_result[mask_grupo].copy()
        if df_grupo.empty:
            continue
        
        # Volume total otimizado do grupo (usar valores atuais do df_result)
        volume_total_grupo = df_result.loc[mask_grupo, 'volume_otimizado'].sum()
        
        # Capacidade máxima do grupo (compartilhada)
        cap_max = df_grupo['capacidade_max'].iloc[0] if df_grupo['capacidade_max'].notna().any() else float('inf')
        
        # Calcular % de uso da capacidade
        if cap_max < float('inf') and cap_max > 0:
            uso_pct = (volume_total_grupo / cap_max) * 100
            # GARANTIR: % nunca excede 100%
            if uso_pct > 100:
                print(f"  ⚠️ [WARNING] Grupo {grupo}: volume ({volume_total_grupo:,.0f}) excede capacidade ({cap_max:,.0f})")
                print(f"      Ajustando volumes para não exceder capacidade...")
                # Se exceder, ajustar os volumes para não exceder capacidade
                fator_limitacao = cap_max / volume_total_grupo
                indices_grupo = df_result[mask_grupo].index
                for idx in indices_grupo:
                    volume_ajustado = df_result.at[idx, 'volume_otimizado'] * fator_limitacao
                    # Não pode exceder demanda individual
                    demanda_individual = df_result.at[idx, 'volume_projetado']
                    volume_final = min(volume_ajustado, demanda_individual)
                    df_result.at[idx, 'volume_otimizado'] = volume_final
                    # Recalcular lucro e margem
                    if 'base_margem_variavel_unit' in df_result.columns:
                        df_result.at[idx, 'lucro_otimizado'] = volume_final * df_result.at[idx, 'base_margem_variavel_unit']
                        df_result.at[idx, 'margem_total_otimizada'] = df_result.at[idx, 'lucro_otimizado']
                
                # Recalcular volume total após ajuste
                volume_total_grupo = df_result.loc[mask_grupo, 'volume_otimizado'].sum()
                uso_pct = min((volume_total_grupo / cap_max) * 100, 100.0)
                print(f"      ✓ Volume após ajuste: {volume_total_grupo:,.0f} UC, % consumo: {uso_pct:.1f}%")
        else:
            uso_pct = 0.0 if volume_total_grupo == 0 else 100.0  # Se sem capacidade definida, mostrar 100% se houver volume
        
        # Atribuir o mesmo % para todos os TIPOs do grupo (capacidade é compartilhada)
        indices_grupo = df_result[mask_grupo].index
        for idx in indices_grupo:
            df_result.at[idx, 'uso_capacidade_pct'] = uso_pct
        
        if cap_max < float('inf'):
            print(f"  Grupo {grupo}: {volume_total_grupo:,.0f} UC / {cap_max:,.0f} UC = {uso_pct:.1f}%")
    
    # Calcular métricas finais
    print("\n[7] Calculando métricas finais...")
    
    # Volume atual = volume_projetado (agregado)
    # IMPORTANTE: Ajustar volume_real para considerar capacidade disponível
    # Se volume_projetado > capacidade, volume_real deve ser limitado pela capacidade
    df_result['volume_atual'] = df_result['volume_projetado'].values
    df_result['volume_real'] = df_result['volume_atual'].values
    
    # Ajustar volume_real por GRUPO DE CAPACIDADE considerando capacidade
    for grupo in grupos_unicos:
        df_grupo = df_result[df_result[coluna_grupo] == grupo].copy()
        if df_grupo.empty:
            continue
        
        cap_max = df_grupo['capacidade_max'].iloc[0] if df_grupo['capacidade_max'].notna().any() else float('inf')
        volume_real_grupo = df_grupo['volume_real'].sum()
        
        # Se volume_real > capacidade, limitar proporcionalmente
        if volume_real_grupo > cap_max and cap_max < float('inf'):
            fator_limitacao = cap_max / volume_real_grupo
            for idx in df_grupo.index:
                df_result.at[idx, 'volume_real'] = df_result.at[idx, 'volume_real'] * fator_limitacao
    
    # Variação
    df_result['variacao_volume'] = df_result['volume_otimizado'].values - df_result['volume_real'].values
    df_result['variacao_volume_pct'] = (
        np.where(
            df_result['volume_real'] > 0,
            (df_result['variacao_volume'] / df_result['volume_real']) * 100,
            0
        )
    )
    df_result['variacao_volume_pct'] = np.clip(df_result['variacao_volume_pct'], -200, 200)
    
    # Margens
    margem_real = (df_result['volume_real'] * df_result['base_margem_variavel_unit']).sum()
    margem_otimizada = (df_result['volume_otimizado'] * df_result['base_margem_variavel_unit']).sum()
    melhoria_margem = margem_otimizada - margem_real
    melhoria_margem_pct = (melhoria_margem / margem_real * 100) if margem_real > 0 else 0
    
    # Estatísticas de capacidade
    n_ok = df_result['dentro_capacidade'].sum() if 'dentro_capacidade' in df_result.columns else 0
    n_total = len(df_result)
    
    print(f"\n[RESULTADO FINAL]")
    print(f"  Margem Real: R$ {margem_real:,.2f}")
    print(f"  Margem Otimizada: R$ {margem_otimizada:,.2f}")
    print(f"  Melhoria: R$ {melhoria_margem:,.2f} ({melhoria_margem_pct:.2f}%)")
    print(f"\n[STATUS DE CAPACIDADE]")
    print(f"  SKUs dentro da capacidade: {n_ok}/{n_total} ({n_ok/n_total*100:.1f}%)")
    if 'status_capacidade' in df_result.columns:
        status_counts = df_result['status_capacidade'].value_counts()
        for status, count in status_counts.items():
            print(f"    {status}: {count} SKUs")
    
    resultado = {
        'df_result': df_result,
        'margem_real': margem_real,
        'margem_otimizada': margem_otimizada,
        'melhoria_margem': melhoria_margem,
        'melhoria_margem_pct': melhoria_margem_pct,
        'resultados_por_tipo': resultados_por_tipo
    }
    
    return resultado

# ============================================================================
# MAIN
# ============================================================================
if __name__ == "__main__":
    # Carregar e preparar dados
    df_work = load_and_prepare_unified_data()
    
    # Otimizar
    resultado = optimize_by_tipo(df_work)
    
    # Salvar resultados
    output_file = "resultado_otimizacao.csv"
    resultado['df_result'].to_csv(output_file, index=False, decimal=',', encoding='utf-8')
    print(f"\n[6] Resultados salvos em: {output_file}")
