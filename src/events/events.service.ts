import {
  BadRequestException,
  Injectable,
  NotFoundException,
  OnApplicationShutdown,
  OnModuleInit,
} from '@nestjs/common';
import { constants, createReadStream } from 'node:fs';
import { access, mkdir, open, stat } from 'node:fs/promises';
import { randomUUID } from 'node:crypto';
import { dirname, join } from 'node:path';
import { createInterface } from 'node:readline';
import { FileHandle } from 'node:fs/promises';

type IndexEntry = {
  offset: number;
  length: number;
};

type StoredEvent = Record<string, unknown> & {
  id: string;
  createdAt: string;
};

@Injectable()
export class EventsService implements OnModuleInit, OnApplicationShutdown {
  private readonly logPath = join(process.cwd(), 'events.log');
  private readonly index = new Map<string, IndexEntry>();
  private fileHandle: FileHandle | null = null;
  private bytes = 0;
  private writeQueue = Promise.resolve();

  async onModuleInit() {
    await this.ensureLogFile();
    await this.recoverIndex();
    this.fileHandle = await open(this.logPath, 'a+');
  }

  async onApplicationShutdown() {
    await this.fileHandle?.close();
    this.fileHandle = null;
  }

  async create(body: unknown): Promise<StoredEvent> {
    if (body === null || Array.isArray(body) || typeof body !== 'object') {
      throw new BadRequestException('Request body must be a JSON object');
    }

    if (!this.fileHandle) {
      throw new Error('Event log is not open');
    }

    const event: StoredEvent = {
      ...(body as Record<string, unknown>),
      id: randomUUID(),
      createdAt: new Date().toISOString(),
    };

    await this.enqueueWrite(event);

    return event;
  }

  async findOne(id: string): Promise<StoredEvent> {
    const entry = this.index.get(id);
    if (!entry) {
      throw new NotFoundException(`Event ${id} was not found`);
    }

    const readHandle = await open(this.logPath, 'r');
    try {
      const buffer = Buffer.alloc(entry.length);
      const { bytesRead } = await readHandle.read(
        buffer,
        0,
        entry.length,
        entry.offset,
      );

      const line = buffer.subarray(0, bytesRead).toString('utf8').trimEnd();
      return JSON.parse(line) as StoredEvent;
    } finally {
      await readHandle.close();
    }
  }

  getStats() {
    return {
      total: this.index.size,
      bytes: this.bytes,
    };
  }

  private async ensureLogFile() {
    await mkdir(dirname(this.logPath), { recursive: true });

    try {
      await access(this.logPath, constants.F_OK);
    } catch {
      const handle = await open(this.logPath, 'w');
      await handle.close();
    }
  }

  private async enqueueWrite(event: StoredEvent) {
    const queuedWrite = this.writeQueue.then(() => this.appendEvent(event));
    this.writeQueue = queuedWrite.catch(() => undefined);
    await queuedWrite;
  }

  private async appendEvent(event: StoredEvent) {
    if (!this.fileHandle) {
      throw new Error('Event log is not open');
    }

    const line = `${JSON.stringify(event)}\n`;
    const offset = this.bytes;
    const length = Buffer.byteLength(line);

    await this.fileHandle.appendFile(line, 'utf8');
    this.index.set(event.id, { offset, length });
    this.bytes += length;
  }

  private async recoverIndex() {
    this.index.clear();
    this.bytes = 0;

    const fileStats = await stat(this.logPath);
    if (fileStats.size === 0) {
      console.log('Recovered 0 events from events.log');
      return;
    }

    let offset = 0;
    let recovered = 0;
    const stream = createReadStream(this.logPath, { encoding: 'utf8' });
    const reader = createInterface({
      input: stream,
      crlfDelay: Infinity,
    });

    for await (const line of reader) {
      if (!line) {
        offset += Buffer.byteLength('\n');
        continue;
      }

      const length = Buffer.byteLength(`${line}\n`);
      const event = JSON.parse(line) as StoredEvent;

      if (typeof event.id === 'string') {
        this.index.set(event.id, { offset, length });
        recovered += 1;
      }

      offset += length;
    }

    this.bytes = fileStats.size;
    console.log(`Recovered ${recovered} events from events.log`);
  }
}
