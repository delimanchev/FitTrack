import { Injectable } from '@nestjs/common';

function required(name: string): string {
  const value = process.env[name];
  if (!value?.trim()) throw new Error(`${name} is required`);
  return value;
}

@Injectable()
export class Settings {
  readonly databaseUrl = required('DATABASE_URL');
  readonly jwtSecret = required('JWT_SECRET');
  readonly jwtIssuer = required('JWT_ISSUER');
  readonly jwtAudience = required('JWT_AUDIENCE');
  readonly userServiceUrl = new URL(required('USER_SERVICE_URL'));
  readonly progressToUserToken = required('PROGRESS_TO_USER_TOKEN');
  readonly internalTokens = [
    required('GOALS_TO_PROGRESS_TOKEN'),
    required('EXERCISE_TO_PROGRESS_TOKEN'),
    required('WORKOUT_TO_PROGRESS_TOKEN'),
  ];

  constructor() {
    if (!['http:', 'https:'].includes(this.userServiceUrl.protocol)) {
      throw new Error('USER_SERVICE_URL must use HTTP or HTTPS');
    }
    if (Buffer.byteLength(this.jwtSecret) < 32) {
      throw new Error('JWT_SECRET must be at least 32 bytes');
    }
  }
}
