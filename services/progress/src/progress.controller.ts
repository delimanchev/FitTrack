import {
  Body, Controller, Delete, Get, HttpCode, Param, ParseIntPipe, Post, Put, Query, UseGuards,
} from '@nestjs/common';
import {
  ApiBearerAuth, ApiCreatedResponse, ApiHeader, ApiNoContentResponse, ApiOkResponse, ApiResponse, ApiSecurity,
} from '@nestjs/swagger';
import { InternalGuard, JwtGuard, UserId } from './auth.js';
import { BodyInput, BodyMeasurement, PageQuery, Weight, WeightInput } from './progress.dto.js';
import { Measurement, ProgressService } from './progress.service.js';

function weightResult(row: Measurement): Weight {
  return { id: row.id, weightKg: row.value, measuredAt: row.measuredAt };
}

function bodyResult(row: Measurement): BodyMeasurement {
  return { id: row.id, area: row.area!, circumferenceCm: row.value, measuredAt: row.measuredAt };
}

@Controller('api/progress')
@UseGuards(JwtGuard)
@ApiBearerAuth()
@ApiResponse({ status: 400, description: 'Invalid input' })
@ApiResponse({ status: 401, description: 'Invalid or missing access token' })
export class ProgressController {
  constructor(private readonly progress: ProgressService) {}

  @Get()
  @ApiOkResponse({ type: [Weight] })
  async weights(@UserId() userId: string, @Query() page: PageQuery) {
    return (await this.progress.list(userId, 'weight', page)).map(weightResult);
  }

  @Get('latest')
  @ApiOkResponse({ type: Weight })
  @ApiResponse({ status: 404, description: 'No weight measurement found' })
  async latestWeight(@UserId() userId: string) {
    return weightResult(await this.progress.latestWeight(userId));
  }

  @Post()
  @ApiCreatedResponse({ type: Weight })
  @ApiResponse({ status: 404, description: 'User not found' })
  @ApiResponse({ status: 503, description: 'User Service unavailable' })
  async createWeight(@UserId() userId: string, @Body() input: WeightInput) {
    const row = await this.progress.create(userId, 'weight', input.weightKg, input.measuredAt);
    return weightResult(row);
  }

  @Put(':id')
  @ApiOkResponse({ type: Weight })
  @ApiResponse({ status: 403, description: 'Measurement belongs to another user' })
  @ApiResponse({ status: 404, description: 'Measurement not found' })
  async updateWeight(@UserId() userId: string, @Param('id', ParseIntPipe) id: number, @Body() input: WeightInput) {
    const row = await this.progress.update(id, userId, 'weight', input.weightKg, input.measuredAt);
    return weightResult(row);
  }

  @Delete(':id')
  @HttpCode(204)
  @ApiNoContentResponse()
  @ApiResponse({ status: 403, description: 'Measurement belongs to another user' })
  @ApiResponse({ status: 404, description: 'Measurement not found' })
  async removeWeight(@UserId() userId: string, @Param('id', ParseIntPipe) id: number) {
    await this.progress.remove(id, userId, 'weight');
  }

  @Get('body-measurements')
  @ApiOkResponse({ type: [BodyMeasurement] })
  async bodyMeasurements(@UserId() userId: string, @Query() page: PageQuery) {
    return (await this.progress.list(userId, 'body', page)).map(bodyResult);
  }

  @Post('body-measurements')
  @ApiCreatedResponse({ type: BodyMeasurement })
  @ApiResponse({ status: 404, description: 'User not found' })
  @ApiResponse({ status: 503, description: 'User Service unavailable' })
  async createBodyMeasurement(@UserId() userId: string, @Body() input: BodyInput) {
    const row = await this.progress.create(userId, 'body', input.circumferenceCm, input.measuredAt, input.area.trim());
    return bodyResult(row);
  }

  @Put('body-measurements/:measurementId')
  @ApiOkResponse({ type: BodyMeasurement })
  @ApiResponse({ status: 403, description: 'Measurement belongs to another user' })
  @ApiResponse({ status: 404, description: 'Measurement not found' })
  async updateBodyMeasurement(
    @UserId() userId: string, @Param('measurementId', ParseIntPipe) id: number, @Body() input: BodyInput,
  ) {
    const row = await this.progress.update(id, userId, 'body', input.circumferenceCm, input.measuredAt, input.area.trim());
    return bodyResult(row);
  }

  @Delete('body-measurements/:measurementId')
  @HttpCode(204)
  @ApiNoContentResponse()
  @ApiResponse({ status: 403, description: 'Measurement belongs to another user' })
  @ApiResponse({ status: 404, description: 'Measurement not found' })
  async removeBodyMeasurement(@UserId() userId: string, @Param('measurementId', ParseIntPipe) id: number) {
    await this.progress.remove(id, userId, 'body');
  }
}

@Controller('progress')
@UseGuards(InternalGuard)
@ApiSecurity('service-token')
export class InternalProgressController {
  constructor(private readonly progress: ProgressService) {}

  @Get('latest')
  @ApiHeader({ name: 'X-User-Id', required: true })
  @ApiOkResponse({ type: Weight })
  @ApiResponse({ status: 400, description: 'User ID is missing or invalid' })
  @ApiResponse({ status: 403, description: 'Invalid service token' })
  @ApiResponse({ status: 404, description: 'No weight measurement found' })
  async latestWeight(@UserId() userId: string) {
    return weightResult(await this.progress.latestWeight(userId));
  }
}
