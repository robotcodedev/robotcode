import * as fs from "fs";

export async function sleep(timeout: number): Promise<number> {
  return new Promise<number>((resolve) => {
    setTimeout(() => resolve(timeout), timeout);
  });
}

export class Mutex {
  private mutex = Promise.resolve();

  lock(): PromiseLike<() => void> {
    let begin: (unlock: () => void) => void = (_unlock) => {
      // empty
    };

    this.mutex = this.mutex.then(() => new Promise(begin));

    return new Promise((resolve) => {
      begin = resolve;
    });
  }

  async dispatch<T>(fn: (() => T) | (() => PromiseLike<T>)): Promise<T> {
    const unlock = await this.lock();
    try {
      return await Promise.resolve(fn()).finally(() => unlock());
    } finally {
      unlock();
    }
  }
}

export class WeakValueMap<K, V extends object> implements Map<K, V> {
  private map = new Map<K, WeakRef<V>>();

  private finalizer = new FinalizationRegistry<K>((v) => {
    this.map.delete(v);
  });

  public clear(): void {
    for (const key of this.map.keys()) {
      this.delete(key);
    }
  }

  public delete(key: K): boolean {
    const ref = this.map.get(key);
    if (ref !== undefined) this.finalizer.unregister(ref);
    this.map.delete(key);
    return true;
  }

  public forEach(callbackfn: (value: V, key: K, map: Map<K, V>) => void, thisArg?: unknown): void {
    for (const [key, value] of this.entries()) {
      callbackfn.bind(thisArg)(value, key, this);
    }
  }

  public get(key: K): V | undefined {
    const w = this.map.get(key);
    if (w !== undefined) return w.deref();
    return undefined;
  }

  public has(key: K): boolean {
    return this.map.has(key);
  }

  public set(key: K, value: V): this {
    if (this.map.has(key)) {
      const oldref = this.map.get(key);
      if (oldref !== undefined) this.finalizer.unregister(oldref);
    }

    const ref = new WeakRef(value);
    this.map.set(key, ref);
    this.finalizer.register(value, key, ref);
    return this;
  }

  public get size(): number {
    return this.map.size;
  }

  [Symbol.iterator](): IterableIterator<[K, V]> {
    return this.entries();
  }

  *entries(): IterableIterator<[K, V]> {
    for (const [key, value] of this.map) {
      const v = value.deref();
      if (v !== undefined) yield [key, v];
    }
  }

  keys(): IterableIterator<K> {
    return this.map.keys();
  }

  *values(): IterableIterator<V> {
    for (const value of this.map.values()) {
      const v = value.deref();
      if (v !== undefined) yield v;
    }
  }

  readonly [Symbol.toStringTag]: string = "WeakValueMap";
}

export class WeakValueSet<V extends object> implements Set<V> {
  private set = new Set<WeakRef<V>>();

  private finalizer = new FinalizationRegistry<WeakRef<V>>((v) => {
    this.set.delete(v);
  });

  add(value: V): this {
    const ref = new WeakRef<V>(value);
    this.set.add(ref);
    this.finalizer.register(value, ref, ref);

    return this;
  }

  clear(): void {
    for (const v of this.set) {
      this.finalizer.unregister(v);
    }
    this.set.clear();
  }

  delete(value: V): boolean {
    if (value === undefined) return false;
    let ref: WeakRef<V> | undefined;
    for (const r of this.set) {
      if (r.deref() === value) {
        ref = r;
        break;
      }
    }
    if (ref === undefined) return false;
    this.set.delete(ref);
    return true;
  }

  forEach(callbackfn: (value: V, value2: V, set: Set<V>) => void, thisArg?: unknown): void {
    for (const [key, value] of this.entries()) {
      callbackfn.bind(thisArg)(value, key, this);
    }
  }

  has(value: V): boolean {
    if (value === undefined) return false;

    for (const r of this.set) {
      if (r.deref() === value) {
        return true;
      }
    }

    return false;
  }

  get size(): number {
    return this.set.size;
  }

  *entries(): IterableIterator<[V, V]> {
    for (const value of this.set) {
      const v = value.deref();
      if (v !== undefined) yield [v, v];
    }
  }

  *keys(): IterableIterator<V> {
    for (const value of this.set) {
      const v = value.deref();
      if (v !== undefined) yield v;
    }
  }

  *values(): IterableIterator<V> {
    for (const value of this.set) {
      const v = value.deref();
      if (v !== undefined) yield v;
    }
  }

  [Symbol.iterator](): IterableIterator<V> {
    return this.values();
  }

  readonly [Symbol.toStringTag]: string = "WeakValueSet";
}

export async function waitForFile(file: string, timeout = 30000): Promise<boolean> {
  const exists = () => fs.existsSync(file);
  const deadline = Date.now() + timeout;

  let result: boolean;

  while (!(result = exists()) && Date.now() < deadline) {
    await sleep(100);
  }

  return result;
}

export async function filterAsync<T>(arr: readonly T[], predicate: (value: T) => Promise<boolean>): Promise<T[]> {
  return await arr.reduce(
    async (memo: T[] | Promise<T[]>, e: T) => ((await predicate(e)) ? [...(await memo), e] : memo),
    [],
  );
}

export function truncateAndReplaceNewlines(str: string, maxLength: number = 50): string {
  // Ersetzt alle Zeilenumbrüche durch Leerzeichen
  const processedString = str.replace(/\r\n|\n|\r/g, " ");

  // Kürzt den String, falls er länger als maxLength ist
  if (processedString.length > maxLength) {
    return processedString.substring(0, maxLength - 3) + "...";
  }
  return processedString;
}
