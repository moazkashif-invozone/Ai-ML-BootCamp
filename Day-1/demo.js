import dotenv from "dotenv";

dotenv.config();
dotenv.config({ path: ".env.example", override: false });

import { AIService } from "./AIService.js";

const ai = new AIService();

async function runDemo() {
  console.log("=== Lead Qualification ===");
  const lead = await ai.qualifyLead({
    name: "Jane Doe",
    company: "Acme Corp",
    role: "VP Engineering",
    message: "We need an enterprise plan for 200 seats by Q3. Budget approved.",
  });
  console.log(lead);

  console.log("\n=== Support Ticket Classifier ===");
  const ticket = await ai.classifySupportTicket(
    "I was charged twice this month and cannot access my dashboard. This is urgent."
  );
  console.log(ticket);

  console.log("\n=== Email Drafter (low temperature) ===");
  const formalEmail = await ai.draftEmail({
    purpose: "Follow up after demo",
    audience: "Prospect CTO",
    context: "They liked the analytics dashboard but asked about SSO.",
    tone: "professional",
    temperature: 0.2,
  });
  console.log(formalEmail);

  console.log("\n=== Email Drafter (high temperature) ===");
  const creativeEmail = await ai.draftEmail({
    purpose: "Follow up after demo",
    audience: "Prospect CTO",
    context: "They liked the analytics dashboard but asked about SSO.",
    tone: "warm and engaging",
    temperature: 0.9,
  });
  console.log(creativeEmail);

  console.log("\n=== Data Extractor ===");
  const extracted = await ai.extractData(
    "Contact: John Smith, john@example.com, +1-555-0100. Order #48291 shipped on June 12.",
    ["name", "email", "phone", "orderId", "shipDate"]
  );
  console.log(extracted);
}

runDemo().catch((error) => {
  console.error(error.message);
  process.exit(1);
});
