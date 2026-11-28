import { createApp } from './app.js';

async function start() {
  const app = await createApp();
  app.enableShutdownHooks();
  try {
    await app.listen(process.env.PORT ?? 8000, '0.0.0.0');
  } catch (error) {
    await app.close();
    throw error;
  }
}

start().catch((error: unknown) => {
  console.error(error);
  process.exitCode = 1;
});
