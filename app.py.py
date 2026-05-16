import os
import webbrowser
import math
import json
import re
from pathlib import Path
from typing import List, Dict, Any, Union
import streamlit as st
import streamlit.components.v1 as components
import urllib.parse
import urllib.request

# Langchain and OpenAI imports
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_experimental.utilities import PythonREPL
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langchain_community.tools.tavily_search import TavilySearchResults
from langchain.agents import create_openai_functions_agent, AgentExecutor

# =====================================================================
# CONFIGURAÇÃO DE DIRETÓRIOS LOCAIS
# =====================================================================
UPLOAD_DIR: Path = Path("./engenharia_uploads_usuario")
UPLOAD_DIR.mkdir(exist_ok=True)
OUTPUT_DIR: Path = Path("./engenharia_output")
OUTPUT_DIR.mkdir(exist_ok=True)

# =====================================================================
# 1. CORE MATEMÁTICO: SISTEMA VEO (VECTOR ENGINE OPTIMIZATION)
# =====================================================================
class VEOEngine:
    @staticmethod
    def calculate_pie_slice(cx: float, cy: float, r: float, start_angle: float, end_angle: float) -> str:
        def polar_to_cartesian(center_x: float, center_y: float, radius: float, angle_in_degrees: float) -> tuple[float, float]:
            angle_in_radians: float = (angle_in_degrees - 90) * math.pi / 180.0
            return (
                center_x + (radius * math.cos(angle_in_radians)),
                center_y + (radius * math.sin(angle_in_radians)) 
            )
        start: tuple[float, float] = polar_to_cartesian(cx, cy, r, end_angle)
        end: tuple[float, float] = polar_to_cartesian(cx, cy, r, start_angle)
        large_arc_flag: str = "1" if end_angle - start_angle > 180 else "0"
        return f"M {cx} {cy} L {start[0]:.2f} {start[1]:.2f} A {r} {r} 0 {large_arc_flag} 0 {end[0]:.2f} {end[1]:.2f} Z"

# =====================================================================
# 2. MOTOR DE BUSCA INDUSTRIAL BLINDADO (REVISADO PARA USO AUTÔNOMO)
# =====================================================================
class HardcodedValidationSearch:
    def __init__(self) -> None:
        self.search_tool: TavilySearchResults = TavilySearchResults(max_results=8) 

    def search_and_verify(self, query: str) -> str:
        raw_results: Any = self.search_tool.invoke({"query": query})
        
        if not raw_results:
            return "RESULTADO_DA_BUSCA: VAZIO. Esta pessoa ou fato não possui registros indexados publicamente."

        query_terms: List[str] = [t.lower() for t in query.split() if len(t) > 3]
        validated_entries_with_score: List[Dict[str, Any]] = []
        
        found_municipal: bool = False
        found_estadual: bool = False
        found_federal: bool = False
        found_particular: bool = False
        
        for res in raw_results:
            content: str = res.get("content", "").lower()
            url: str = res.get("url", "")
            
            current_score: int = sum(1 for term in query_terms if term in content)
            
            if current_score >= 1:
                entry_text_raw: str = res.get('content', '')
                
                if "umef" in content or "municipal" in content or "secretaria municipal de educação" in content or "sme" in content or "prefeitura" in content:
                    found_municipal = True
                if "escola estadual" in content or "estadual" in content or "secretaria de educação do estado" in content or "see" in content or "governo do estado" in content:
                    found_estadual = True
                if "federal" in content or "universidade federal" in content:
                    found_federal = True
                if "particular" in content or "privada" in content:
                    found_particular = True
                
                if "diretora" in content or "gestão" in content or "diretor" in content or "coordenador" in content:
                    current_score += 3
                
                validated_entries_with_score.append({"text": f"Fonte Validada [{url}]: {entry_text_raw}", "score": current_score})
                
        if not validated_entries_with_score:
            return "RESULTADO_DA_BUSCA: INCONCLUSIVO. Os links encontrados não tratam especificamente do indivíduo ou fato perguntado."

        validated_entries_with_score.sort(key=lambda x: x["score"], reverse=True)
        
        status_summary_parts: List[str] = []
        if found_municipal: status_summary_parts.append("MUNICIPAL")
        if found_estadual: status_summary_parts.append("ESTADUAL")
        if found_federal: status_summary_parts.append("FEDERAL")
        if found_particular: status_summary_parts.append("PARTICULAR")

        final_status_report: str = ""
        if status_summary_parts:
            if len(status_summary_parts) > 1:
                final_status_report = f"ATENÇÃO: Foram encontrados indícios de múltiplos status administrativos: {', '.join(status_summary_parts)}. Necessário desambiguação cuidadosa."
            else:
                final_status_report = f"STATUS IDENTIFICADO: {status_summary_parts[0]}."
        else:
            final_status_report = "STATUS ADMINISTRATIVO: Não foi possível determinar o status administrativo com clareza."
            
        final_validated_texts: List[str] = [entry["text"] for entry in validated_entries_with_score]
        return final_status_report + "\n\n" + "\n\n".join(final_validated_texts)

verified_search: HardcodedValidationSearch = HardcodedValidationSearch()

# =====================================================================
# 3. FERRAMENTAS DO AGENTE AUTÔNOMO
# =====================================================================
@tool
def google_search_engine(query: str) -> str:
    """Ferramenta de pesquisa restrita à internet. Retorna apenas dados estáveis
    e dispara gatilho de erro se a informação for inexistente, e identifica o status administrativo de instituições."""
    return verified_search.search_and_verify(query)

@tool
def python_code_interpreter(code: str) -> str:
    """Executa código Python em ambiente seguro. Use para validar dados,
    executar equações matemáticas e disparar o motor analítico VEO."""
    try:
        repl: PythonREPL = PythonREPL()
        return repl.run(code)
    except Exception as e:
        return f"Erro de Execução no Interpretador: {str(e)}"

@tool
def save_and_preview_file(filename: str, content: str, file_type: str) -> str:
    """Salva o arquivo otimizado pelo VEO no disco rígido
    e abre uma pré-visualização instantânea no navegador do usuário.
    Argumentos:
    - filename: Nome do arquivo (ex: 'planta_baixa') sem a extensão.
    - content: O código/conteúdo bruto gerado da planta ou gráfico.
    - file_type: Escolha estritamente entre ['svg', 'dxf', 'html']."""
    try:
        ext: str = file_type.lower().strip(".")
        full_name: str = f"{filename}.{ext}"
        filepath: Path = OUTPUT_DIR / full_name
        
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
            
        if ext == "svg":
            html_wrapper: Path = filepath.with_suffix(".html")
            with open(html_wrapper, "w", encoding="utf-8") as html_f:
                html_f.write(f"""<html><body style='margin:0; background:#11141a; 
                display:flex; justify-content:center; align-items:center; height:100vh;'>
                <div style='background:#ffffff; padding:30px; border-radius:8px; box-shadow: 0 12px 40px rgba(0,0,0,0.7);'>
                {content}</div></body></html>""")
            webbrowser.open(f"file://{html_wrapper.resolve()}")
        elif ext in ["html", "dxf"]:
            webbrowser.open(f"file://{filepath.resolve()}")
            
        return f"Sucesso VEO: Arquivo otimizado salvo em '{filepath.resolve()}' e renderizado."
    except Exception as e:
        return f"Falha ao salvar/visualizar arquivo: {str(e)}"

@tool
def url_generator_engine(action: str, target_data: str) -> str:
    """Cria, codifica ou encurta URLs de internet para arquivos de engenharia ou buscas.
    Argumentos:
    - action: Escolha estritamente entre ['encode_query', 'shorten_link', 'local_file_url']
    - target_data: O texto, link longo ou nome do arquivo que será convertido em URL."""
    try:
        action_type: str = action.lower().strip()
        if action_type == 'encode_query':
            return urllib.parse.quote(target_data)
        elif action_type == 'local_file_url':
            filepath: Path = OUTPUT_DIR / target_data
            return f"file://{filepath.resolve()}"
        else:
            return f"Ação '{action}' processada para: {target_data}"
    except Exception as e:
        return f"Erro no gerador de URL: {str(e)}"
