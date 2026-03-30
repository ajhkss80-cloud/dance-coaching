import { EnvConfig, loadConfig } from "../infrastructure/config/env.js";
import { RedisConnection } from "../infrastructure/redis/RedisConnection.js";
import { BullMQAdapter } from "../infrastructure/queue/BullMQAdapter.js";
import { LocalStorageAdapter } from "../infrastructure/storage/LocalStorageAdapter.js";
import { StartGeneration } from "../application/use-cases/StartGeneration.js";
import { GetJobStatus } from "../application/use-cases/GetJobStatus.js";
import { StartCoaching } from "../application/use-cases/StartCoaching.js";
import { GetCoachResult } from "../application/use-cases/GetCoachResult.js";
import { IJobQueue } from "../application/ports/IJobQueue.js";
import { IStorage } from "../application/ports/IStorage.js";

export interface Container {
  config: EnvConfig;
  redis: RedisConnection | null;
  jobQueue: IJobQueue;
  storage: IStorage;
  startGeneration: StartGeneration;
  getJobStatus: GetJobStatus;
  startCoaching: StartCoaching;
  getCoachResult: GetCoachResult;
  shutdown(): Promise<void>;
}

export interface ContainerOverrides {
  jobQueue?: IJobQueue;
  storage?: IStorage;
}

export function createContainer(
  configOverrides?: Partial<Record<string, string>>,
  deps?: ContainerOverrides
): Container {
  const config = loadConfig(configOverrides);

  let redis: RedisConnection | null = null;
  let bullAdapter: BullMQAdapter | null = null;

  const jobQueue: IJobQueue =
    deps?.jobQueue ??
    (() => {
      redis = new RedisConnection(config.REDIS_URL);
      bullAdapter = new BullMQAdapter("dance-coaching", redis.getClient());
      return bullAdapter;
    })();

  const storage: IStorage =
    deps?.storage ?? new LocalStorageAdapter(config.STORAGE_DIR);

  const startGeneration = new StartGeneration(jobQueue, storage);
  const getJobStatus = new GetJobStatus(jobQueue);
  const startCoaching = new StartCoaching(jobQueue);
  const getCoachResult = new GetCoachResult(jobQueue);

  return {
    config,
    redis,
    jobQueue,
    storage,
    startGeneration,
    getJobStatus,
    startCoaching,
    getCoachResult,
    async shutdown() {
      if (bullAdapter) {
        await bullAdapter.close();
      }
      if (redis) {
        await redis.disconnect();
      }
    },
  };
}
