import { Injectable, Logger, OnModuleDestroy, OnModuleInit } from '@nestjs/common';
import { readFile } from 'node:fs/promises';
import { join } from 'node:path';
import { Pool } from 'pg';
import { Settings } from './settings.js';

@Injectable()
export class Database implements OnModuleInit, OnModuleDestroy {
  readonly pool: Pool;

  constructor(settings: Settings) {
    this.pool = new Pool({
      connectionString: settings.databaseUrl,
      max: 4,
      connectionTimeoutMillis: 5000,
    });
    this.pool.on('error', (error: Error) => {
      Logger.error(error.message, 'PostgreSQL');
    });
  }

  async onModuleInit() {
    const sql = await readFile(join(import.meta.dirname, '../migrations/001_initial.sql'), 'utf8');
    const client = await this.pool.connect();
    try {
      await client.query('BEGIN');
      // Serialize migrations if two instances start at the same time.
      await client.query('SELECT pg_advisory_xact_lock(41006)');
      await client.query(sql);
      await client.query('COMMIT');
    } catch (error) {
      await client.query('ROLLBACK');
      throw error;
    } finally {
      client.release();
    }
  }

  async onModuleDestroy() {
    await this.pool.end();
  }
}
