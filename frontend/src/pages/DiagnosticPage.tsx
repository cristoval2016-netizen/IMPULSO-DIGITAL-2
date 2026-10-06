import { useEffect, useState, type FormEvent } from "react";
import { api } from "../api";
import { label, type DiagnosticResult, type Questionnaire, type Sector } from "../types";

type Step = "empresa" | "preguntas" | "consentimiento" | "resultado";

const emptyCompany = { name: "", nit: "", sector: "comercio" as Sector, city: "", employees: 1, website: "" };
const emptyContact = { full_name: "", email: "", phone: "", position: "" };

export default function DiagnosticPage() {
  const [q, setQ] = useState<Questionnaire | null>(null);
  const [step, setStep] = useState<Step>("empresa");
  const [company, setCompany] = useState(emptyCompany);
  const [contact, setContact] = useState(emptyContact);
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [qIndex, setQIndex] = useState(0);
  const [consent, setConsent] = useState(false);
  const [marketing, setMarketing] = useState(false);
  const [result, setResult] = useState<DiagnosticResult | null>(null);
  const [error, setError] = useState("");
  const [sending, setSending] = useState(false);

  useEffect(() => {
    api<Questionnaire>("/api/public/questionnaire").then(setQ).catch((e) => setError(e.message));
  }, []);

  const submit = async () => {
    setSending(true);
    setError("");
    try {
      const clean = (o: Record<string, unknown>) =>
        Object.fromEntries(Object.entries(o).map(([k, v]) => [k, v === "" ? null : v]));
      const res = await api<DiagnosticResult>("/api/public/diagnostics", {
        method: "POST",
        body: JSON.stringify({
          company: clean(company),
          contact: clean(contact),
          answers,
          data_consent: consent,
          marketing_consent: marketing,
        }),
      });
      setResult(res);
      setStep("resultado");
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setSending(false);
    }
  };

  const onCompanySubmit = (e: FormEvent) => {
    e.preventDefault();
    setStep("preguntas");
  };

  const question = q?.questions[qIndex];
  const progress = q ? Math.round((Object.keys(answers).length / q.questions.length) * 100) : 0;

  const choose = (value: string) => {
    if (!q || !question) return;
    setAnswers((a) => ({ ...a, [question.code]: value }));
    setTimeout(() => {
      if (qIndex < q.questions.length - 1) setQIndex((i) => i + 1);
      else setStep("consentimiento");
    }, 180);
  };

  return (
    <div className="public">
      <header className="hero">
        <div className="brand light">Impulso<span>Digital</span></div>
        <h1>Diagnóstico de madurez digital <em>gratuito</em></h1>
        <p>Descubra en 5 minutos qué tan digital es su Pyme y qué pasos tomar para vender más.</p>
      </header>

      <section className="card wizard">
        {error && <div className="alert">{error}</div>}

        {step === "empresa" && (
          <form onSubmit={onCompanySubmit} className="grid-form">
            <h2>1. Datos de su empresa</h2>
            <label>Nombre de la empresa *
              <input required minLength={2} value={company.name}
                onChange={(e) => setCompany({ ...company, name: e.target.value })} />
            </label>
            <label>NIT
              <input value={company.nit} placeholder="900123456"
                onChange={(e) => setCompany({ ...company, nit: e.target.value })} />
            </label>
            <label>Sector económico *
              <select value={company.sector}
                onChange={(e) => setCompany({ ...company, sector: e.target.value as Sector })}>
                <option value="comercio">Comercio</option>
                <option value="servicios">Servicios</option>
                <option value="manufactura">Manufactura</option>
              </select>
            </label>
            <label>Número de empleados *
              <input type="number" min={1} required value={company.employees}
                onChange={(e) => setCompany({ ...company, employees: Number(e.target.value) })} />
            </label>
            <label>Ciudad
              <input value={company.city} onChange={(e) => setCompany({ ...company, city: e.target.value })} />
            </label>
            <label>Sitio web
              <input value={company.website} placeholder="https://"
                onChange={(e) => setCompany({ ...company, website: e.target.value })} />
            </label>

            <h2>Datos de contacto</h2>
            <label>Nombre completo *
              <input required minLength={2} value={contact.full_name}
                onChange={(e) => setContact({ ...contact, full_name: e.target.value })} />
            </label>
            <label>Correo electrónico *
              <input type="email" required value={contact.email}
                onChange={(e) => setContact({ ...contact, email: e.target.value })} />
            </label>
            <label>Celular / WhatsApp
              <input value={contact.phone} onChange={(e) => setContact({ ...contact, phone: e.target.value })} />
            </label>
            <label>Cargo
              <input value={contact.position} onChange={(e) => setContact({ ...contact, position: e.target.value })} />
            </label>
            <div className="actions full">
              <button className="btn primary" disabled={!q}>Comenzar diagnóstico →</button>
            </div>
          </form>
        )}

        {step === "preguntas" && q && question && (
          <div>
            <div className="progress"><div style={{ width: `${progress}%` }} /></div>
            <small className="muted">
              Pregunta {qIndex + 1} de {q.questions.length} · {label(question.dimension)}
            </small>
            <h2>{question.text}</h2>
            <div className="options">
              {question.options.map((o) => (
                <button key={o.value}
                  className={`option ${answers[question.code] === o.value ? "selected" : ""}`}
                  onClick={() => choose(o.value)}>
                  {o.label}
                </button>
              ))}
            </div>
            <div className="actions">
              <button className="btn ghost"
                onClick={() => (qIndex === 0 ? setStep("empresa") : setQIndex((i) => i - 1))}>
                ← Atrás
              </button>
              {answers[question.code] && qIndex < q.questions.length - 1 && (
                <button className="btn ghost" onClick={() => setQIndex((i) => i + 1)}>Siguiente →</button>
              )}
            </div>
          </div>
        )}

        {step === "consentimiento" && (
          <div>
            <h2>Último paso: autorización de datos</h2>
            <div className="legal">
              En cumplimiento de la <strong>Ley 1581 de 2012</strong> y el Decreto 1377 de 2013,
              Impulso Digital tratará sus datos personales con la finalidad de generar su diagnóstico,
              contactarle con la propuesta comercial y gestionar la relación con su empresa. Usted
              puede conocer, actualizar, rectificar y suprimir sus datos, y revocar esta autorización
              en cualquier momento escribiendo a <em>datos@impulsodigital.co</em>. La información de
              su empresa se trata bajo estricta confidencialidad.
            </div>
            <label className="check">
              <input type="checkbox" checked={consent} onChange={(e) => setConsent(e.target.checked)} />
              <span>Autorizo de manera previa, expresa e informada el tratamiento de mis datos personales
                conforme a la Política de Tratamiento de Datos. *</span>
            </label>
            <label className="check">
              <input type="checkbox" checked={marketing} onChange={(e) => setMarketing(e.target.checked)} />
              <span>Acepto recibir información comercial y contenidos educativos (opcional).</span>
            </label>
            <div className="actions">
              <button className="btn ghost" onClick={() => setStep("preguntas")}>← Revisar respuestas</button>
              <button className="btn primary" disabled={!consent || sending} onClick={submit}>
                {sending ? "Calculando…" : "Ver mi resultado"}
              </button>
            </div>
          </div>
        )}

        {step === "resultado" && result && <ResultView r={result} />}
      </section>
    </div>
  );
}

function ResultView({ r }: { r: DiagnosticResult }) {
  return (
    <div className="result">
      <h2>Resultado para {r.company_name}</h2>
      <div className="score-row">
        <div className={`score-circle lvl-${r.maturity_level}`}>
          <span>{Math.round(r.total_score)}</span><small>/100</small>
        </div>
        <div>
          <p className="muted">Nivel de madurez digital</p>
          <h3>{r.maturity_label}</h3>
          <p className="muted">Sector: {label(r.sector)}</p>
        </div>
      </div>

      <h3>Puntaje por dimensión</h3>
      <div className="bars">
        {Object.entries(r.dimension_scores).map(([d, s]) => (
          <div className="bar" key={d}>
            <span>{label(d)}</span>
            <div className="track"><div style={{ width: `${s}%` }} /></div>
            <b>{Math.round(s)}</b>
          </div>
        ))}
      </div>

      <h3>Recomendaciones prioritarias</h3>
      <ol className="recs">{r.recommendations.map((t) => <li key={t}>{t}</li>)}</ol>

      <div className="package">
        <small>Paquete recomendado</small>
        <h3>{r.recommended_package.name}</h3>
        <p>{r.recommended_package.description}</p>
        <p className="muted">Un asesor de Impulso Digital le contactará pronto para presentarle su propuesta.</p>
      </div>
    </div>
  );
}
