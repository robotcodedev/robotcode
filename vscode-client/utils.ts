export async function sleep(timeout: number): Promise<number> {
    return new Promise<number>((resolve) => {
        setTimeout(() => resolve(timeout), timeout);
    });
}

export async function waitForPromise<T>(promise: Promise<T>, timeout: number): Promise<T | null> {
    // Set a timer that will resolve with null
    return new Promise<T | null>((resolve, reject) => {
        const timer = setTimeout(() => resolve(null), timeout);
        promise
            .then((result) => {
                // When the promise resolves, make sure to clear the timer or
                // the timer may stick around causing tests to wait
                clearTimeout(timer);
                resolve(result);
            })
            .catch((e) => {
                clearTimeout(timer);
                reject(e);
            });
    });
}

export class Mutex {
    private mutex = Promise.resolve();

    lock(): PromiseLike<() => void> {
        let begin: (unlock: () => void) => void = (unlock) => {};

        this.mutex = this.mutex.then(() => {
            return new Promise(begin);
        });

        return new Promise((res) => {
            begin = res;
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
