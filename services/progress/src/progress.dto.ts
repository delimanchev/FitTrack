import { ApiProperty, ApiPropertyOptional } from '@nestjs/swagger';
import { Type } from 'class-transformer';
import { IsDateString, IsInt, IsNumber, IsPositive, IsString, Length, Matches, Max, Min } from 'class-validator';

class MeasurementDate {
  @ApiProperty({ format: 'date', example: '2026-11-28' })
  @Matches(/^[1-9]\d{3}-\d{2}-\d{2}$/)
  @IsDateString({ strict: true })
  measuredAt!: string;
}

export class WeightInput extends MeasurementDate {
  @ApiProperty({ example: 85.5, minimum: 0, exclusiveMinimum: true, maximum: 1000 })
  @IsNumber()
  @IsPositive()
  @Max(1000)
  weightKg!: number;
}

export class BodyInput extends MeasurementDate {
  @ApiProperty({ example: 'waist', maxLength: 60 })
  @IsString()
  @Length(1, 60)
  @Matches(/\S/)
  area!: string;

  @ApiProperty({ example: 82, minimum: 0, exclusiveMinimum: true, maximum: 1000 })
  @IsNumber()
  @IsPositive()
  @Max(1000)
  circumferenceCm!: number;
}

export class Weight extends WeightInput {
  @ApiProperty({ example: 1 })
  id!: number;
}

export class BodyMeasurement extends BodyInput {
  @ApiProperty({ example: 2 })
  id!: number;
}

export class PageQuery {
  @ApiPropertyOptional({ default: 50, minimum: 1, maximum: 100 })
  @Type(() => Number)
  @IsInt()
  @Min(1)
  @Max(100)
  limit = 50;

  @ApiPropertyOptional({ default: 0, minimum: 0, maximum: 2147483647 })
  @Type(() => Number)
  @IsInt()
  @Min(0)
  @Max(2147483647)
  offset = 0;
}
