export class FileTools {
  async readFile(path: string): Promise<string> {
    return await Deno.readTextFile(path);
  }

  async createFile(path: string, content: string): Promise<string> {
    await Deno.writeTextFile(path, content);
    return `Created file at ${path}`;
  }
}

export function makeFileTools(): FileTools {
  return new FileTools();
}
