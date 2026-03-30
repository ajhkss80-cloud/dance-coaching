import Redis from "ioredis";
import type { FastifyPluginAsync } from "fastify";
import fp from "fastify-plugin";

export class RedisConnection {
  private client: Redis;

  constructor(url: string) {
    this.client = new Redis(url, {
      maxRetriesPerRequest: null,
      enableReadyCheck: false,
      lazyConnect: true,
    });
  }

  getClient(): Redis {
    return this.client;
  }

  async connect(): Promise<void> {
    await this.client.connect();
  }

  async disconnect(): Promise<void> {
    await this.client.quit();
  }

  isConnected(): boolean {
    return this.client.status === "ready";
  }
}

declare module "fastify" {
  interface FastifyInstance {
    redis: RedisConnection;
  }
}

const redisPlugin: FastifyPluginAsync<{ url: string }> = async (fastify, opts) => {
  const redis = new RedisConnection(opts.url);
  await redis.connect();

  fastify.decorate("redis", redis);

  fastify.addHook("onClose", async () => {
    await redis.disconnect();
  });
};

export const fastifyRedis = fp(redisPlugin, {
  name: "fastify-redis",
});
