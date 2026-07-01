import OpenAI from "openai";

export class AIService {
  constructor(
    apiKey = process.env.GROQ_API_KEY || process.env.GROK_API_KEY || process.env.XAI_API_KEY || process.env.OPENAI_API_KEY,
    model = process.env.GROQ_MODEL || process.env.GROK_MODEL || process.env.XAI_MODEL || "llama-3.1-8b-instant",
    baseURL = process.env.GROQ_BASE_URL || process.env.GROK_BASE_URL || process.env.XAI_BASE_URL || "https://api.groq.com/openai/v1"
  ) {
    if (!apiKey) {
      throw new Error("GROQ_API_KEY, GROK_API_KEY, XAI_API_KEY, or OPENAI_API_KEY is required");
    }

    this.client = new OpenAI({ apiKey, baseURL });
    this.model = model;
  }

  async _chat({ system, user, temperature = 0.2, responseFormat }) {
    const response = await this.client.chat.completions.create({
      model: this.model,
      temperature,
      ...(responseFormat ? { response_format: responseFormat } : {}),
      messages: [
        { role: "system", content: system },
        { role: "user", content: user },
      ],
    });

    return response.choices[0]?.message?.content?.trim() ?? "";
  }

  /**
   * Evaluates a sales lead and returns qualification details.
   * @param {string|object} leadInfo - Raw lead text or structured lead fields
   */
  async qualifyLead(leadInfo) {
    const leadText =
      typeof leadInfo === "string" ? leadInfo : JSON.stringify(leadInfo, null, 2);

    const system = `You are a B2B sales lead qualification assistant.
Analyze the lead and respond with valid JSON only using this schema:
{
  "qualified": boolean,
  "score": number (0-100),
  "priority": "high" | "medium" | "low",
  "reasoning": string,
  "recommendedNextStep": string,
  "keySignals": string[]
}
Score based on budget fit, urgency, decision-maker access, and product fit.`;

    const content = await this._chat({
      system,
      user: `Qualify this lead:\n\n${leadText}`,
      temperature: 0.1,
      responseFormat: { type: "json_object" },
    });

    return JSON.parse(content);
  }

  /**
   * Classifies a support ticket by category, priority, and sentiment.
   * @param {string} ticketText - Raw support ticket content
   */
  async classifySupportTicket(ticketText) {
    const system = `You are a customer support triage assistant.
Classify the ticket and respond with valid JSON only using this schema:
{
  "category": "billing" | "technical" | "account" | "shipping" | "feature_request" | "other",
  "priority": "critical" | "high" | "medium" | "low",
  "sentiment": "angry" | "frustrated" | "neutral" | "positive",
  "summary": string,
  "suggestedTeam": string,
  "requiresEscalation": boolean
}`;

    const content = await this._chat({
      system,
      user: `Classify this support ticket:\n\n${ticketText}`,
      temperature: 0,
      responseFormat: { type: "json_object" },
    });

    return JSON.parse(content);
  }

  /**
   * Drafts a professional email. Higher temperature = more creative wording.
   * @param {object} options
   * @param {string} options.purpose - Goal of the email (e.g. "follow up", "apology")
   * @param {string} options.audience - Who the email is for
   * @param {string} options.context - Background details to include
   * @param {string} [options.tone="professional"] - Desired tone
   * @param {number} [options.temperature=0.7] - Creativity level (0 = deterministic, 1 = creative)
   */
  async draftEmail({
    purpose,
    audience,
    context,
    tone = "professional",
    temperature = 0.7,
  }) {
    const system = `You are an expert business email writer.
Write a clear, concise email with a subject line.
Return valid JSON only using this schema:
{
  "subject": string,
  "body": string
}
Match the requested tone. Do not invent facts not provided in the context.`;

    const user = `Purpose: ${purpose}
Audience: ${audience}
Tone: ${tone}
Context:
${context}`;

    const content = await this._chat({
      system,
      user,
      temperature,
      responseFormat: { type: "json_object" },
    });

    return JSON.parse(content);
  }

  /**
   * Extracts structured data from unstructured raw text.
   * @param {string} rawText - Source text to parse
   * @param {string[]|object} fields - Field names or schema describing what to extract
   */
  async extractData(rawText, fields) {
    const fieldDescription = Array.isArray(fields)
      ? fields.join(", ")
      : JSON.stringify(fields, null, 2);

    const system = `You are a precise data extraction assistant.
Extract the requested fields from the text.
Return valid JSON only. Use null for missing values.
Do not guess or fabricate data that is not present in the source text.`;

    const user = `Extract these fields:
${fieldDescription}

Source text:
${rawText}`;

    const content = await this._chat({
      system,
      user,
      temperature: 0,
      responseFormat: { type: "json_object" },
    });

    return JSON.parse(content);
  }
}

export default AIService;
