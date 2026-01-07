import { DurableObject } from "cloudflare:workers";

// MotivateM3 Cloudflare Worker
// Worker handles HTTP requests
// Durable object holds per-user state (memory)

export class MotivateSessionDO extends DurableObject<Env> {
	async sayHello(name: string): Promise<string> {
		const count = (await this.ctx.storage.get<number>("count")) ?? 0;
		const newCount = count + 1;

		await this.ctx.storage.put("count", newCount);

		return `Hello, ${name}. Call count for this user: ${newCount}`;
	}
}

export default {
	async fetch(request: Request, env: Env): Promise<Response> {
		const url = new URL(request.url);
		const userId = url.searchParams.get("userId") ?? "demo_user";

		// Get the durable object instance for this user
		const stub = env.MY_DURABLE_OBJECT.getByName(userId);

		const greeting = await stub.sayHello("world");
		return new Response(greeting);
	},
} satisfies ExportedHandler<Env>;
