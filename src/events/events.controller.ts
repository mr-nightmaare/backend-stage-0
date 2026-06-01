import {
  Body,
  Controller,
  Get,
  HttpCode,
  HttpStatus,
  Param,
  Post,
} from '@nestjs/common';
import { EventsService } from './events.service';

@Controller()
export class EventsController {
  constructor(private readonly eventsService: EventsService) {}

  @Post('events')
  @HttpCode(HttpStatus.CREATED)
  async create(@Body() body: unknown) {
    return this.eventsService.create(body);
  }

  @Get('events/:id')
  async findOne(@Param('id') id: string) {
    return this.eventsService.findOne(id);
  }

  @Get('stats')
  getStats() {
    return this.eventsService.getStats();
  }
}
