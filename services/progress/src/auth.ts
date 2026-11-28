import {
  BadRequestException, CanActivate, createParamDecorator, ExecutionContext,
  ForbiddenException, Injectable, UnauthorizedException,
} from '@nestjs/common';
import { timingSafeEqual } from 'node:crypto';
import { IncomingHttpHeaders } from 'node:http';
import jwt from 'jsonwebtoken';
import { Settings } from './settings.js';

type AuthRequest = { headers: IncomingHttpHeaders; userId: string };

export const UserId = createParamDecorator(
  (_data: unknown, context: ExecutionContext) =>
    context.switchToHttp().getRequest<AuthRequest>().userId,
);

@Injectable()
export class JwtGuard implements CanActivate {
  constructor(private readonly settings: Settings) {}

  canActivate(context: ExecutionContext): boolean {
    const request = context.switchToHttp().getRequest<AuthRequest>();
    const token = /^Bearer (\S+)$/i.exec(request.headers.authorization ?? '')?.[1];
    if (!token) throw new UnauthorizedException('A valid access token is required');

    try {
      const payload = jwt.verify(token, this.settings.jwtSecret, {
        algorithms: ['HS256'],
        issuer: this.settings.jwtIssuer,
        audience: this.settings.jwtAudience,
      });
      if (
        typeof payload === 'string' || typeof payload.exp !== 'number' ||
        typeof payload.sub !== 'string' || !payload.sub.trim() || payload.sub.length > 200
      ) {
        throw new Error('Missing or invalid JWT claims');
      }
      request.userId = payload.sub;
    } catch {
      throw new UnauthorizedException('A valid access token is required');
    }
    return true;
  }
}

@Injectable()
export class InternalGuard implements CanActivate {
  constructor(private readonly settings: Settings) {}

  canActivate(context: ExecutionContext): boolean {
    const request = context.switchToHttp().getRequest<AuthRequest>();
    const header = request.headers['x-service-token'];
    const token = Buffer.from(typeof header === 'string' ? header : '');
    const accepted = this.settings.internalTokens.some((secret) => {
      const expected = Buffer.from(secret);
      return token.length === expected.length && timingSafeEqual(token, expected);
    });
    if (!accepted) throw new ForbiddenException('Invalid service token');

    const userId = request.headers['x-user-id'];
    if (typeof userId !== 'string' || !userId.trim() || userId.length > 200) {
      throw new BadRequestException('X-User-Id is required');
    }
    request.userId = userId;
    return true;
  }
}
