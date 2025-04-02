from fastapi import FastAPI, HTTPException, Depends
from sqlmodel import Field, Session, SQLModel, create_engine, select
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

app = FastAPI()

db_url = "sqlite:///./db.sqlite3"
engine = create_engine(db_url, echo=False)

class Atendimento(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    cid: str
    operadora: str
    plano: str
    procedimentos: str
    nome_paciente: Optional[str] = None
    timestamp: str
    glosa: Optional[bool] = None

SQLModel.metadata.create_all(engine)

cids = {
    "K40.0": "Hérnia inguinal bilateral com obstrução, sem gangrena",
}

procedimentos = {
    "04.06.01.012-3": {
        "descricao": "Hernioplastia inguinal bilateral",
        "valores": {
            ("Unimed", "Unimed Clássico"): 1500.00
        }
    }
}

recomendacoes = {
    ("K40.0", "Unimed", "Unimed Clássico"): [
        "04.06.01.012-3"
    ]
}

operadoras = {
    "Unimed": ["Unimed Clássico", "Unimed Alfa"],
    "Amil": ["Amil 400", "Amil 700"],
    "Bradesco": ["Bradesco Top", "Bradesco Flex"]
}

class RecomendacaoRequest(BaseModel):
    cid: str
    operadora: str
    plano: str

class ProcedimentoInfo(BaseModel):
    codigo: str
    descricao: str
    valor_estimado: Optional[float] = None

class AtendimentoRequest(BaseModel):
    cid: str
    operadora: str
    plano: str
    procedimentos: List[str]
    nome_paciente: Optional[str] = None

class FeedbackGlosaRequest(BaseModel):
    id: int
    glosa: bool

@app.get("/cid/{codigo}")
def get_cid_descricao(codigo: str):
    if codigo in cids:
        return {"codigo": codigo, "descricao": cids[codigo]}
    raise HTTPException(status_code=404, detail="CID não encontrado")

@app.get("/operadoras")
def listar_operadoras():
    return {"operadoras": operadoras}

@app.post("/recomendacao", response_model=List[ProcedimentoInfo])
def get_recomendacoes(req: RecomendacaoRequest):
    key = (req.cid, req.operadora, req.plano)
    if key not in recomendacoes:
        raise HTTPException(status_code=404, detail="Nenhuma recomendação encontrada")

    resultados = []
    for cod in recomendacoes[key]:
        proc = procedimentos.get(cod)
        if proc:
            valor = proc["valores"].get((req.operadora, req.plano))
            resultados.append(ProcedimentoInfo(
                codigo=cod,
                descricao=proc["descricao"],
                valor_estimado=valor
            ))
    return resultados

@app.get("/procedimento/{codigo}")
def get_procedimento_info(codigo: str):
    if codigo in procedimentos:
        return procedimentos[codigo]
    raise HTTPException(status_code=404, detail="Procedimento não encontrado")

@app.post("/atendimento")
def registrar_atendimento(req: AtendimentoRequest):
    novo = Atendimento(
        cid=req.cid,
        operadora=req.operadora,
        plano=req.plano,
        procedimentos=",".join(req.procedimentos),
        nome_paciente=req.nome_paciente,
        timestamp=datetime.now().isoformat(),
        glosa=None
    )
    with Session(engine) as session:
        session.add(novo)
        session.commit()
    return {"mensagem": "Atendimento registrado com sucesso"}

@app.get("/atendimentos")
def listar_atendimentos():
    with Session(engine) as session:
        atend = session.exec(select(Atendimento)).all()
        return {"historico": [
            {
                "id": a.id,
                "cid": a.cid,
                "operadora": a.operadora,
                "plano": a.plano,
                "procedimentos": a.procedimentos.split(","),
                "nome_paciente": a.nome_paciente,
                "timestamp": a.timestamp,
                "glosa": a.glosa
            } for a in atend
        ]}

@app.post("/feedback-glosa")
def feedback_glosa(req: FeedbackGlosaRequest):
    with Session(engine) as session:
        atendimento = session.get(Atendimento, req.id)
        if not atendimento:
            raise HTTPException(status_code=404, detail="Atendimento não encontrado")
        atendimento.glosa = req.glosa
        session.add(atendimento)
        session.commit()
    return {"mensagem": "Feedback de glosa registrado"}
    if __name__ == "__main__":
    import uvicorn
    import os

    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port)