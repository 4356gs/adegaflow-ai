import { describe, expect, it } from "vitest";
import { adaptRunResult, assumptionLabels, emailClipboard, formatEuro, guardAnalysis, guardAssumptions, guardRecommendation, memorySourceLabel, proposalClipboard, writePlainText } from "@/lib/commercial-result";
import { vi } from "vitest";
import { completeResult, EMAIL_ID, INQUIRY_ID, RUN_ID } from "./commercial-fixture";

describe("commercial result adapters", () => {
  it("adapts the real complete backend shape into closed view models", () => {
    const result = adaptRunResult(completeResult(), RUN_ID, "completed");
    expect(result.analysis.state).toBe("available"); expect(result.recommendation.state).toBe("available"); expect(result.quote.state).toBe("available"); expect(result.artifacts.map(a=>a.kind)).toEqual(["proposal","email"]);
  });
  it("rejects mismatched ids and statuses at the top envelope", () => {
    expect(()=>adaptRunResult(completeResult({agent_run_id:EMAIL_ID}),RUN_ID,"completed")).toThrow();
    expect(()=>adaptRunResult(completeResult({status:"failed"}),RUN_ID,"completed")).toThrow();
  });
  it("rejects invalid envelopes, invalid dates and non-finite values", () => {
    expect(()=>adaptRunResult({...completeResult(),warnings:"bad"},RUN_ID,"completed")).toThrow();
    const invalid=completeResult(); invalid.memory_summary[0]!.created_at="not-date"; expect(()=>adaptRunResult(invalid,RUN_ID,"completed")).toThrow();
    expect(guardRecommendation({...completeResult().recommendation,total_bottles:Infinity})).toBeNull();
  });
  it("isolates null, future and malformed opaque sections", () => {
    const payload=completeResult({analysis:null,recommendation:{schema_version:"2.0"},quote:null,artifacts:[{id:EMAIL_ID,artifact_type:"future",language:"es",schema_version:"2.0",content:{secret:"never"},review_status:"future",created_at:"2026-08-05T12:00:00Z"}]});
    const result=adaptRunResult(payload,RUN_ID,"completed"); expect(result.analysis.state).toBe("missing"); expect(result.recommendation.state).toBe("incompatible"); expect(result.quote.state).toBe("missing"); expect(result.artifacts[0]?.kind).toBe("incompatible");
  });
  it("guards exact versioned objects and seven assumptions", () => {
    expect(guardAnalysis(completeResult().analysis)).not.toBeNull(); expect(guardRecommendation(completeResult().recommendation)).not.toBeNull(); expect(guardAssumptions(completeResult().quote?.assumptions)).not.toBeNull(); expect(assumptionLabels()).toHaveLength(7);
    expect(guardAssumptions({...completeResult().quote?.assumptions,future:true})).toBeNull();
  });
  it("formats zero and euro cents without treating them as absent", () => { expect(formatEuro(0)).toMatch(/0,00/); expect(formatEuro(1)).toMatch(/0,01/); expect(formatEuro(999)).toMatch(/9,99/); });
  it("composes plain clipboard payloads with mandatory prefixes and separation", () => {
    const result=adaptRunResult(completeResult(),RUN_ID,"completed"); const p=result.artifacts.find(a=>a.kind==="proposal"); const e=result.artifacts.find(a=>a.kind==="email");
    if (!p || p.kind!=="proposal" || !e || e.kind!=="email") throw new Error("fixtures");
    expect(proposalClipboard(p.value)).toMatch(/^BORRADOR — REQUIERE REVISIÓN HUMANA/); expect(emailClipboard(e.value)).toMatch(/^BORRADOR — NO ENVIADO/); expect(emailClipboard(e.value)).not.toContain(e.value.subject); expect(proposalClipboard(p.value)).not.toContain(p.value.id);
  });
  it("labels all memory provenance solely from source inquiry id",()=>{ expect(memorySourceLabel(INQUIRY_ID,INQUIRY_ID)).toBe("Consulta actual"); expect(memorySourceLabel(EMAIL_ID,INQUIRY_ID)).toBe("Interacción anterior"); expect(memorySourceLabel(null,INQUIRY_ID)).toBe("Procedencia no disponible"); });
  it("reports clipboard success, rejection and absence without modifying text",async()=>{const ok={writeText:vi.fn(async()=>undefined)};expect(await writePlainText("plain",ok)).toBe("Copiado");expect(ok.writeText).toHaveBeenCalledWith("plain");expect(await writePlainText("plain",{writeText:vi.fn(async()=>{throw new Error("denied")})})).toBe("No se pudo copiar");expect(await writePlainText("plain",undefined)).toBe("No se pudo copiar");});
});
