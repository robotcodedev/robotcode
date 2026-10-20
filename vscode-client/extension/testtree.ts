// Builds the items of a TestController from the model of a discovery, the one way from the model to the tree. It
// changes only what differs, so that an equal result changes no item and VS Code keeps the expansion of the tree.
import * as vscode from "vscode";

import { RobotItemType, RobotTestItem } from "./testdiscovery";
import { WeakValueMap } from "./utils";

export interface TestTreeTags {
  // the tags of an item, from the tag names of its discovery
  tagsOf(names: string[] | undefined): vscode.TestTag[];
  // the tag that marks the workspace folder of an item, which the run profiles of the folder carry too
  folderTagOf(item: vscode.TestItem): vscode.TestTag | undefined;
}

/**
 * The URI that tells the workspace folder of an item: its own, or that of the nearest item above it. The top-level
 * suite that Robot Framework creates for several paths has no source and no URI; the workspace item above it has the
 * folder's URI.
 */
export function folderUriOf(item: vscode.TestItem): vscode.Uri | undefined {
  for (let current: vscode.TestItem | undefined = item; current !== undefined; current = current.parent) {
    if (current.uri !== undefined) return current.uri;
  }
  return undefined;
}

function toRange(range: NonNullable<RobotTestItem["range"]>): vscode.Range {
  return new vscode.Range(range.start.line, range.start.character, range.end.line, range.end.character);
}

function arraysEqual<T>(a: T[] | undefined, b: T[] | undefined): boolean {
  if (a === b) return true;
  if (a === undefined || b === undefined) return false;
  if (a.length !== b.length) return false;
  for (let i = 0; i < a.length; i++) if (a[i] !== b[i]) return false;
  return true;
}

export class TestTreeBuilder {
  private readonly items = new WeakValueMap<string, vscode.TestItem>();
  // the tag IDs last set per item, so that equal tags are not set again
  private readonly lastSetTags = new Map<string, string[]>();

  constructor(
    private readonly controller: vscode.TestController,
    private readonly tags: TestTreeTags,
  ) {}

  public get(id: string): vscode.TestItem | undefined {
    return this.items.get(id);
  }

  /**
   * Makes the item of `robotItem` below `parent`, or among the root items without a parent, match it and its
   * children. A suite or workspace item without children and without an error is removed instead, as it would only
   * sit in the tree as an empty node; the result is then undefined.
   */
  public build(parent: vscode.TestItem | undefined, robotItem: RobotTestItem): vscode.TestItem | undefined {
    const item = this.addOrUpdate(parent, robotItem);
    if (item.canResolveChildren) {
      this.buildChildren(item, robotItem.children ?? []);
      if (item.children.size === 0 && item.error === undefined) {
        this.remove(parent, item.id);
        return undefined;
      }
    }
    return item;
  }

  /** Makes the children of `item` match `robotItems`, and removes the children that are not among them. */
  public buildChildren(item: vscode.TestItem, robotItems: RobotTestItem[]): void {
    const kept = new Set<string>();
    for (const robotItem of robotItems) {
      const child = this.build(item, robotItem);
      if (child !== undefined) kept.add(child.id);
    }
    const others: string[] = [];
    item.children.forEach((child) => {
      if (!kept.has(child.id)) others.push(child.id);
    });
    for (const id of others) this.remove(item, id);
  }

  /** Removes the item with `id` below `parent`, or among the root items, and everything below it. */
  public remove(parent: vscode.TestItem | undefined, id: string): void {
    const collection = parent ? parent.children : this.controller.items;
    const item = collection.get(id);
    if (item === undefined) return;
    const children: string[] = [];
    item.children.forEach((child) => {
      children.push(child.id);
    });
    for (const child of children) this.remove(item, child);
    collection.delete(id);
    this.items.delete(id);
    this.lastSetTags.delete(id);
  }

  private addOrUpdate(parent: vscode.TestItem | undefined, robotItem: RobotTestItem): vscode.TestItem {
    const canResolveChildren = robotItem.type === RobotItemType.SUITE || robotItem.type === RobotItemType.WORKSPACE;
    const collection = parent ? parent.children : this.controller.items;

    let item = collection.get(robotItem.id);
    if (item === undefined) {
      item = this.controller.createTestItem(
        robotItem.id,
        robotItem.name,
        robotItem.uri ? vscode.Uri.parse(robotItem.uri) : undefined,
      );
      this.items.set(robotItem.id, item);
      collection.add(item);
    }

    if (item.canResolveChildren !== canResolveChildren) item.canResolveChildren = canResolveChildren;

    if (robotItem.range !== undefined) {
      const range = toRange(robotItem.range);
      if (item.range === undefined || !item.range.isEqual(range)) item.range = range;
    }

    if (item.label !== robotItem.name) item.label = robotItem.name;

    const description =
      robotItem.type === RobotItemType.TEST ||
      robotItem.type === RobotItemType.TASK ||
      robotItem.type === RobotItemType.SUITE
        ? `${robotItem.type} ${robotItem.description ? ` - ${robotItem.description}` : ""}`
        : robotItem.description;
    if (item.description !== description) item.description = description;

    if (item.error !== robotItem.error) item.error = robotItem.error;

    const folderTag = this.tags.folderTagOf(item);
    const tagIds = [...(robotItem.tags ?? [])];
    if (folderTag !== undefined) tagIds.push(folderTag.id);
    if (!arraysEqual(this.lastSetTags.get(robotItem.id), tagIds)) {
      const tags = this.tags.tagsOf(robotItem.tags);
      if (folderTag !== undefined) tags.push(folderTag);
      item.tags = tags;
      this.lastSetTags.set(robotItem.id, tagIds);
    }

    return item;
  }
}
