import { DurableObject } from "cloudflare:workers";

// MotivateM3 Cloudflare Worker
// Worker handles HTTP requests

type ChatMsg = { role: "system"| "user" | "assistant"; content: string };

//
export interface Env{
	MY_DURABLE_OBJECT: DurableObjectNamespace;
	AI:Ai;
}

// Durable object holds per-user state (memory)
export class MotivateSessionDO extends DurableObject<Env> {
	private env: Env;

	constructor(ctx: DurableObjectState, env: Env) {
		super(ctx, env);
		this.env = env;
	}

	async chat(message: string): Promise<string> {
		const history = 
		(await this.ctx.storage.get<ChatMsg[]>("history")) ?? 
		[
			{
				role: "system",
				content:
				"Be supportive, concise and practical. Ask one short follow-up question only when needed.",
			},
		];

		history.push({role: "user", content: message });

		// Call Workers AI (Llama 3.3)
		const model = "@cf/meta/llama-3.3-70b-instruct-fp8-fast";

		const aiResult = await this.env.AI.run(model, {
			messages: history,
		});

		const reply =
			(aiResult as any)?.response ??
      		(aiResult as any)?.result ??
      		"Sorry — I couldn’t generate a response right now.";

    	history.push({ role: "assistant", content: String(reply) });

		// Keep last 20 messages
		const trimmed =
      		history[0]?.role === "system"
			? [history[0], ...history.slice(-20)]
			: history.slice(-20);

    	await this.ctx.storage.put("history", trimmed);
		return String(reply);
	}
}

// Worker (HTTP API)
const corsHeaders: Record<string, string>={}