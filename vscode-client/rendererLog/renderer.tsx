import { h, Fragment, Component, createRef, createContext, RefObject } from "preact";

interface ResultData {
  node_type: "message" | "root" | "keyword";
}

interface RootResultData extends ResultData {
  node_type: "root";
  items: ResultData[];
}

interface MessageResultData extends ResultData {
  node_type: "message";

  id: string;
  message: string;
  level: string;
  html: boolean;
  timestamp?: string;
}

interface KeywordResultData extends ResultData {
  node_type: "keyword";

  id: string;
  name: string;
  owner: string;
  source_name: string;
  doc: string;
  args: string[];
  assign: string[];
  tags: string[];
  timeout?: string;
  type: string;
  status: string;
  start_time: string;
  end_time: string;
  elapsed_time: string;

  items: ResultData[];
}

export interface ExpandableContextType {
  registerChild: (ref: RefObject<Expandable>) => void;
  unregisterChild: (ref: RefObject<Expandable>) => void;
  get parentThis(): RefObject<Expandable> | null;
}

const ExpandableContext = createContext<Partial<ExpandableContextType>>({
  registerChild: () => {},
  unregisterChild: () => {},
  get parentThis() {
    return null;
  },
});

interface ExpandableProps {
  header?: string | h.JSX.Element;
  collapsed?: boolean;
  collapsible?: boolean;
  title?: string;
  focusable?: boolean;
  rootContainer?: boolean;
}

class Expandable extends Component<ExpandableProps> {
  private childRefs: RefObject<Expandable>[] = [];
  private ref: RefObject<Expandable> = createRef();
  private childrenRef = createRef<HTMLDivElement>();
  private togglerRef = createRef<HTMLDivElement>();
  private headerRef = createRef<HTMLDivElement>();

  public registerChild(ref: RefObject<Expandable>): void {
    if (ref && !this.childRefs.includes(ref)) {
      this.childRefs.push(ref);
    }
  }

  public unregisterChild(ref: RefObject<Expandable>): void {
    this.childRefs = this.childRefs.filter((childRef) => childRef !== ref);
  }

  get isCollapsible(): boolean {
    return this.props.collapsible !== false ? true : false;
  }

  get isFocusable(): boolean {
    return this.props.focusable !== false ? true : false;
  }

  get isCollapsed(): boolean {
    return this.childrenRef.current?.getAttribute("data-collapsed") === "true";
  }

  get isRootContainer(): boolean {
    return this.props.rootContainer === true ? true : false;
  }

  get isExpanded(): boolean {
    return !this.isCollapsed;
  }

  componentWillMount?(): void {
    try {
      const parentContext = this.context as ExpandableContextType;
      parentContext?.registerChild(this.ref);
    } catch (e) {
      console.log(e);
    }
  }

  get parent(): Expandable | null {
    const parentContext = this.context as ExpandableContextType;
    return parentContext?.parentThis?.current ? parentContext.parentThis.current : null;
  }

  get root(): Expandable | null {
    let parent = this.parent;
    while (parent) {
      if (parent.parent) {
        parent = parent.parent;
      } else {
        return parent;
      }
    }
    return null;
  }

  componentDidMount(): void {
    this.ref.current = this;
  }

  expand(): void {
    if (this.isCollapsible) {
      this.childrenRef.current?.setAttribute("data-collapsed", "false");
      this.togglerRef.current?.setAttribute("data-collapsed", "false");
      this.props.collapsed = false;
    }
  }

  collapse(): void {
    if (this.isCollapsible) {
      this.childrenRef.current?.setAttribute("data-collapsed", "true");
      this.togglerRef.current?.setAttribute("data-collapsed", "true");
      this.props.collapsed = true;
    }
  }

  toggle(): void {
    if (this.isCollapsed) {
      this.expand();
    } else {
      this.collapse();
    }
  }

  expandAll(): void {
    this.expand();

    this.childRefs.forEach((ref) => ref.current?.expandAll());
  }

  collapseAll(onlyChildren?: boolean): void {
    if (!onlyChildren) {
      this.collapse();
    }

    this.childRefs.forEach((ref) => ref.current?.collapseAll());
  }

  renderHeader(): h.JSX.Element {
    {
      return <Fragment>{this.props.header ? this.props.header : <>&nbsp;</>}</Fragment>;
    }
  }

  renderItems(): h.JSX.Element {
    return (
      <ExpandableContext.Provider
        value={{
          registerChild: (c) => this.registerChild(c),
          unregisterChild: (c) => this.unregisterChild(c),
          parentThis: this.ref,
        }}
      >
        {this.props.children}
      </ExpandableContext.Provider>
    );
  }

  isElementInViewport(element: HTMLElement): boolean {
    const elementRect = element.getBoundingClientRect();
    const root = this.root?.childrenRef.current?.closest("expandable-root") ?? document.body;
    if (root) {
      const containerRect = root.getBoundingClientRect();

      return elementRect.bottom >= containerRect.top && elementRect.top < containerRect.bottom;
    }
    return (
      elementRect.top >= 0 &&
      elementRect.left >= 0 &&
      elementRect.bottom <= window.innerHeight &&
      elementRect.right <= window.innerWidth
    );
  }

  ensureElementInView(element: HTMLElement | null | undefined) {
    if (element && !this.isElementInViewport(element)) {
      element.scrollIntoView({ block: "nearest", inline: "nearest" });
    }
  }

  focusHeader(): void {
    if (this.isFocusable) {
      this.ensureElementInView(this.headerRef.current);
      this.headerRef.current?.focus({ preventScroll: true });
    }
  }

  handleKeyDown(event: KeyboardEvent): void {
    const element = this.headerRef.current;
    const shadowRoot = element?.getRootNode() as ShadowRoot | Document;

    if (element && element === shadowRoot.activeElement) {
      switch (event.key) {
        case "ArrowLeft":
          event.stopPropagation();
          if (this.isCollapsed) {
            this.parent?.focusHeader();
          } else {
            this.collapse();
          }
          break;
        case "ArrowRight":
          event.stopPropagation();
          if (this.isExpanded) {
            this.getFirstChild()?.focusHeader();
          } else {
            this.expand();
          }
          break;
        case "ArrowDown":
          event.preventDefault();
          event.stopPropagation();
          if (this.isExpanded && this.childRefs.length > 0) {
            // Gehe zum ersten Kind, wenn der aktuelle Knoten expandiert ist
            this.childRefs[0].current?.focusHeader();
          } else {
            let current: Expandable | null = this!;
            while (current) {
              const parent: Expandable | null = current?.parent;
              if (!parent) break; // Wurzel erreicht, nichts mehr zu traversieren

              const index = parent.childRefs.indexOf(current.ref);
              if (index < parent.childRefs.length - 1) {
                // Gehe zum nächsten Geschwister des Elternknotens
                parent.childRefs[index + 1].current?.focusHeader();
                return;
              }
              // Traverse zur übergeordneten Ebene
              current = parent;
            }
          }
          break;
        case "ArrowUp":
          event.preventDefault();
          event.stopPropagation();

          if (this.parent) {
            const index = this.parent.childRefs.indexOf(this.ref);

            if (index > 0) {
              let prevSibling = this.parent.childRefs[index - 1]?.current;
              while (prevSibling?.isExpanded && prevSibling.childRefs.length > 0) {
                prevSibling = prevSibling.childRefs[prevSibling.childRefs.length - 1]?.current;
              }
              prevSibling?.focusHeader();
            } else {
              this.parent.focusHeader();
            }
          }
          break;

        case "Home":
          if (this.root && this.root.childRefs.length) {
            event.preventDefault();
            event.stopPropagation();

            this.root.getFirstChild()?.focusHeader();
          }
          break;
        case "End":
          if (this.root && this.root.childRefs.length) {
            event.preventDefault();
            event.stopPropagation();

            this.root?.getLastExpandedChild()?.focusHeader();
          }
          break;
        case "PageUp":
          if (this.root && this.root.childRefs.length) {
            event.preventDefault();
            event.stopPropagation();

            this.root.getFirstChild()?.focusHeader();
          }
          break;
        case "PageDown":
          if (this.root && this.root.childRefs.length) {
            event.preventDefault();
            event.stopPropagation();

            this.root?.getLastExpandedChild()?.focusHeader();
          }
          break;
        default:
          break;
      }
    }
  }

  handleWheel(event: WheelEvent): void {
    const element = this.childrenRef.current;

    if (element) {
      const isAtTop = element.scrollTop === 0 && event.deltaY < 0;
      const isAtBottom = element.scrollTop + element.clientHeight >= element.scrollHeight && event.deltaY > 0;

      if (!isAtTop && !isAtBottom) {
        event.stopPropagation();
      }
    }
  }

  getFirstChild(): Expandable | null | undefined {
    if (this.childRefs.length > 0) {
      return this.childRefs[0].current ?? undefined;
    }
    return null;
  }

  getLastChild(): Expandable | null | undefined {
    if (this.childRefs.length > 0) {
      return this.childRefs[this.childRefs.length - 1].current ?? undefined;
    }
    return undefined;
  }

  getLastExpandedChild(): Expandable | null | undefined {
    let lastChild = this.getLastChild();
    while (lastChild?.isExpanded && lastChild.childRefs.length > 0) {
      lastChild = lastChild.getLastChild();
    }
    return lastChild;
  }

  render(): h.JSX.Element {
    return (
      <Fragment>
        <div
          ref={this.headerRef}
          {...(this.isFocusable ? { tabIndex: 0 } : {})}
          class={this.isRootContainer ? "expander-root-header" : "expander-header"}
          onKeyDown={(event) => {
            this.handleKeyDown(event);
          }}
          onClick={(event) => {
            event.stopPropagation();
            this.toggle();
            this.headerRef.current?.focus();
          }}
        >
          {this.isRootContainer ? (
            <div class="expander-root-header-left" title={this.props.title}>
              {/* {this.renderHeader()} */}
            </div>
          ) : (
            <div class="expander-header-left" title={this.props.title}>
              {this.renderHeader()}
            </div>
          )}

          <div class="expander-header-right">
            <span
              class="expander-icon expand-all"
              title="Expand all"
              onClick={(event) => {
                event.stopPropagation();
                this.expandAll();
              }}
            />
            <span
              class="expander-icon collapse-all"
              title="Collapse all"
              onClick={(event) => {
                event.stopPropagation();
                this.collapseAll();
              }}
            />
            {/* <span
              class="expander-icon link"
              onClick={(event) => {
                event.stopPropagation();
                this.collapseAll();
              }}
            /> */}
          </div>
          {this.isCollapsible ? (
            <span
              ref={this.togglerRef}
              class={`expander-icon toggle ${this.props.collapsed ? "closed" : "open"}`}
              data-collapsed={this.props.collapsed}
              onClick={(event) => {
                event.stopPropagation();
                this.toggle();
              }}
            ></span>
          ) : null}
        </div>

        <div
          ref={this.childrenRef}
          onWheel={(event) => {
            if (this.isRootContainer) this.handleWheel(event);
          }}
          data-collapsed={this.props.collapsed}
          // class={`children ${this.isCollapsible ? "collapsible" : ""} ${this.props.collapsed ? "closed" : "open"}`}
          class={`children ${this.isCollapsible ? "collapsible" : ""} ${this.isRootContainer ? "root-container" : ""}`}
        >
          {this.renderItems()}
        </div>
      </Fragment>
    );
  }
}

Expandable.contextType = ExpandableContext;

class RootResultRenderer extends Component<{ data: RootResultData }> {
  renderItems(): h.JSX.Element {
    return <Fragment>{this.props.data.items.map((child) => renderResultData(child))}</Fragment>;
  }

  render(): h.JSX.Element {
    return (
      <div class="result-body expandable-root">
        <Expandable focusable={false} collapsible={false} rootContainer={true}>
          {this.renderItems()}
        </Expandable>
      </div>
    );
  }
}

class MessageResultRenderer extends Component<{ data: MessageResultData }> {
  render(): h.JSX.Element {
    const level_lower = this.props.data.level.toLocaleLowerCase();
    return (
      <table id={this.props.data.id} class={`messages ${level_lower}-message`}>
        <tr class="message-row">
          <td class="time">{this.props.data.timestamp}</td>
          <td class={`${level_lower} level`}>
            <span class={`label ${level_lower}`}>{this.props.data.level}</span>
          </td>
          {this.props.data.html ? (
            <td class="message" dangerouslySetInnerHTML={{ __html: this.props.data.message }}></td>
          ) : (
            <td class="message">{this.props.data.message}</td>
          )}
        </tr>
      </table>
    );
  }
}

interface KeywordProps extends ExpandableProps {
  data: KeywordResultData;
}

class Keyword extends Component<KeywordProps> {
  renderHeader(): h.JSX.Element {
    {
      return (
        <Fragment>
          <span class="elapsed" title="Elapsed time">
            {this.props.data.elapsed_time}
          </span>
          <span class={`label ${this.props.data.status.toLowerCase()}`}>{this.props.data.type}</span>
          <span class="assign">{this.props.data.assign.join("    ")}</span>
          <span class="name">
            {this.props.data.owner ? <span class="parent-name">{this.props.data.owner} . </span> : null}
            {this.props.data.name}
          </span>
          &nbsp;
          <span class="arg">{this.props.data.args}</span>
        </Fragment>
      );
    }
  }

  renderItems(): h.JSX.Element {
    return (
      <Fragment>
        <table class="metadata keyword-metadata">
          {this.props.data.doc ? (
            <tr>
              <th>Documentation:</th>
              <td class="doc" dangerouslySetInnerHTML={{ __html: this.props.data.doc }}></td>
            </tr>
          ) : null}
          {this.props.data.tags && this.props.data.tags.length > 0 ? (
            <tr>
              <th>Tags:</th>
              <td class="tags">{this.props.data.tags.join(", ")}</td>
            </tr>
          ) : null}
          {this.props.data.timeout ? (
            <tr>
              <th>Tags:</th>
              <td class="tags">{this.props.data.timeout}</td>
            </tr>
          ) : null}
          <tr>
            <th>Start / End / Elapsed:</th>
            <td>
              {this.props.data.start_time} / ${this.props.data.elapsed_time} / ${this.props.data.elapsed_time}
            </td>
          </tr>
        </table>
        {this.props.data.items.map((child) => renderResultData(child))}
      </Fragment>
    );
  }

  render(): h.JSX.Element {
    const result = (
      <div class="keyword">
        <Expandable
          header={this.renderHeader()}
          collapsed={this.props.data.status !== "FAIL" ? true : false}
          title={`${this.props.data.type} ${this.props.data.owner ? this.props.data.owner + "." + this.props.data.name : this.props.data.name} [${this.props.data.status}]`}
        >
          {this.renderItems()}
        </Expandable>
      </div>
    );
    return result;
  }
}

function renderResultData(data: ResultData): h.JSX.Element {
  switch (data.node_type) {
    case "root":
      return <RootResultRenderer data={data as RootResultData} />;
    case "message":
      return <MessageResultRenderer data={data as MessageResultData} />;
    case "keyword":
      return <Keyword data={data as KeywordResultData}></Keyword>;
    default:
      return <div>Unknown node type</div>;
  }
}

interface RendererProps {
  data: ResultData;
}

export class Renderer extends Component<RendererProps> {
  render(): h.JSX.Element {
    return renderResultData(this.props.data);
  }
}
