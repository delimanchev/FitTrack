import 'reflect-metadata';
import { Module, NestApplicationOptions, ValidationPipe } from '@nestjs/common';
import { NestFactory } from '@nestjs/core';
import { DocumentBuilder, SwaggerModule } from '@nestjs/swagger';
import { InternalGuard, JwtGuard } from './auth.js';
import { Database } from './database.js';
import { InternalProgressController, ProgressController } from './progress.controller.js';
import { ProgressService } from './progress.service.js';
import { Settings } from './settings.js';

@Module({
  controllers: [ProgressController, InternalProgressController],
  providers: [Settings, Database, ProgressService, JwtGuard, InternalGuard],
})
class ProgressModule {}

export async function createApp(options: NestApplicationOptions = {}) {
  const app = await NestFactory.create(ProgressModule, { abortOnError: false, ...options });
  app.useGlobalPipes(new ValidationPipe({ transform: true, whitelist: true, forbidNonWhitelisted: true }));

  const config = new DocumentBuilder()
    .setTitle('FitTrack Progress')
    .setVersion('1.0')
    .addBearerAuth()
    .addApiKey({ type: 'apiKey', in: 'header', name: 'X-Service-Token' }, 'service-token')
    .build();
  SwaggerModule.setup('docs', app, () => SwaggerModule.createDocument(app, config), {
    jsonDocumentUrl: '/openapi.json',
    raw: ['json'],
  });
  return app;
}
