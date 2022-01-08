import * as os from "os";
import * as net from "net";

export function getLocalHosts(): Set<string | undefined> {
  const interfaces = os.networkInterfaces();

  // Add undefined value for createServer function to use default host,
  // and default IPv4 host in case createServer defaults to IPv6.
  const results = new Set([undefined, "0.0.0.0"]);

  for (const _interface of Object.values(interfaces)) {
    if (_interface) {
      for (const config of _interface) {
        results.add(config.address);
      }
    }
  }

  return results;
}

function checkAvailablePort(port?: number, host?: string): Promise<number> {
  return new Promise((resolve, reject) => {
    const server = net.createServer();
    server.unref();
    server.on("error", reject);

    server.listen(port, host, () => {
      const p = server.address() as net.AddressInfo;

      server.close(() => {
        resolve(p.port);
      });
    });
  });
}

export function isErrnoException(object: unknown): object is NodeJS.ErrnoException {
  return Object.prototype.hasOwnProperty.call(object, "code") || Object.prototype.hasOwnProperty.call(object, "errno");
}

export async function getAvailablePort(hosts: string[], port?: number): Promise<number | undefined> {
  for (const host of hosts) {
    try {
      port = await checkAvailablePort(port, host);
    } catch (error) {
      if (!isErrnoException(error) || error.code === undefined || !["EADDRNOTAVAIL", "EINVAL"].includes(error.code)) {
        throw error;
      }
    }
  }

  return port;
}
