import * as vscode from "vscode";
import {
    RetireEvent,
    TestAdapter,
    TestEvent,
    TestLoadFinishedEvent,
    TestLoadStartedEvent,
    TestRunFinishedEvent,
    TestRunStartedEvent,
    TestSuiteEvent,
    TestSuiteInfo,
} from "vscode-test-adapter-api";

export class RobotTestAdapter implements TestAdapter {
    private readonly testsEmitter = new vscode.EventEmitter<TestLoadStartedEvent | TestLoadFinishedEvent>();
    private readonly testStatesEmitter = new vscode.EventEmitter<
        TestRunStartedEvent | TestRunFinishedEvent | TestSuiteEvent | TestEvent
    >();
    private readonly autorunEmitter = new vscode.EventEmitter<void>();
    private readonly retireEmitter = new vscode.EventEmitter<RetireEvent>();

    get tests(): vscode.Event<TestLoadStartedEvent | TestLoadFinishedEvent> {
        return this.testsEmitter.event;
    }
    get testStates(): vscode.Event<TestRunStartedEvent | TestRunFinishedEvent | TestSuiteEvent | TestEvent> {
        return this.testStatesEmitter.event;
    }
    get autorun(): vscode.Event<void> | undefined {
        return this.autorunEmitter.event;
    }
    get retire(): vscode.Event<RetireEvent> | undefined {
        return this.retireEmitter.event;
    }

    constructor(public readonly workspace: vscode.WorkspaceFolder) {}

    async load() {
        this.testsEmitter.fire(<TestLoadStartedEvent>{ type: "started" });

        let tests: TestSuiteInfo = {
            type: "suite",
            id: "1",
            label: this.workspace.name,
            description: "Hello World",
            tooltip: "rumba",
            debuggable: true,

            children: [
                {
                    type: "suite",
                    id: "2",
                    label: "rumba",
                    children: [
                        {
                            type: "test",
                            id: "3",
                            label: "first test",
                            debuggable: true
                        }
                    ]

                }
            ],
        };

        this.testsEmitter.fire(<TestLoadFinishedEvent>{ type: "finished", suite: tests });
    }
    async run(tests: string[]): Promise<void> {
        throw new Error("Method not implemented.");
    }
    cancel(): void {
        throw new Error("Method not implemented.");
    }
    dispose(): void {
        throw new Error("Method not implemented.");
    }
}
