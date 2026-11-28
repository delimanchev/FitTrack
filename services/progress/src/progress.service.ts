import {
  BadRequestException, ForbiddenException, Injectable, NotFoundException, ServiceUnavailableException,
} from '@nestjs/common';
import { Database } from './database.js';
import { PageQuery } from './progress.dto.js';
import { Settings } from './settings.js';

type Kind = 'weight' | 'body';

export type Measurement = {
  id: number;
  value: number;
  area: string | null;
  measuredAt: string;
};

const columns = 'id, value, area, measured_at::text AS "measuredAt"';

@Injectable()
export class ProgressService {
  constructor(private readonly db: Database, private readonly settings: Settings) {}

  async list(userId: string, kind: Kind, { limit, offset }: PageQuery) {
    const result = await this.db.pool.query<Measurement>(
      `SELECT ${columns} FROM measurements
       WHERE user_id = $1 AND kind = $2
       ORDER BY measured_at DESC, id DESC LIMIT $3 OFFSET $4`,
      [userId, kind, limit, offset],
    );
    return result.rows;
  }

  async latestWeight(userId: string) {
    const [weight] = await this.list(userId, 'weight', { limit: 1, offset: 0 });
    if (!weight) throw new NotFoundException('No weight measurement found');
    return weight;
  }

  async create(userId: string, kind: Kind, value: number, measuredAt: string, area: string | null = null) {
    await this.verifyUser(userId);
    const result = await this.db.pool.query<Measurement>(
      `INSERT INTO measurements (user_id, kind, value, measured_at, area)
       VALUES ($1, $2, $3, $4, $5) RETURNING ${columns}`,
      [userId, kind, value, measuredAt, area],
    );
    return result.rows[0];
  }

  async update(
    id: number, userId: string, kind: Kind, value: number, measuredAt: string, area: string | null = null,
  ) {
    this.checkId(id);
    const result = await this.db.pool.query<Measurement>(
      `UPDATE measurements SET value = $4, measured_at = $5, area = $6
       WHERE id = $1 AND user_id = $2 AND kind = $3 RETURNING ${columns}`,
      [id, userId, kind, value, measuredAt, area],
    );
    if (!result.rows[0]) await this.measurementError(id, kind);
    return result.rows[0];
  }

  async remove(id: number, userId: string, kind: Kind) {
    this.checkId(id);
    const result = await this.db.pool.query(
      'DELETE FROM measurements WHERE id = $1 AND user_id = $2 AND kind = $3',
      [id, userId, kind],
    );
    if (result.rowCount === 0) await this.measurementError(id, kind);
  }

  private checkId(id: number) {
    if (!Number.isInteger(id) || id < 1 || id > 2147483647) {
      throw new BadRequestException('Invalid measurement ID');
    }
  }

  private async measurementError(id: number, kind: Kind): Promise<never> {
    const result = await this.db.pool.query('SELECT 1 FROM measurements WHERE id = $1 AND kind = $2', [id, kind]);
    if (!result.rowCount) throw new NotFoundException('Measurement not found');
    throw new ForbiddenException('This measurement belongs to another user');
  }

  private async verifyUser(userId: string) {
    const url = new URL(`/users/${encodeURIComponent(userId)}`, this.settings.userServiceUrl);
    let status: number;
    try {
      const response = await fetch(url, {
        headers: { 'X-Service-Token': this.settings.progressToUserToken },
        signal: AbortSignal.timeout(2000),
        redirect: 'error',
      });
      status = response.status;
      await response.body?.cancel();
    } catch {
      throw new ServiceUnavailableException('User Service is unavailable');
    }
    if (status === 404) throw new NotFoundException('User does not exist');
    if (status !== 200) throw new ServiceUnavailableException('User Service is unavailable');
  }
}
