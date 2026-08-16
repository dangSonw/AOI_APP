class NodeNotImplementedError(NotImplementedError):
    def __init__(self, node_id: str) -> None:
        super().__init__(f'Node runtime {node_id} has not been implemented.')
        self.node_id = node_id


class NodeArtifactIntegrityError(RuntimeError):
    pass


class NodeExecutionCancelled(RuntimeError):
    pass


class NodeExecutionContextRequired(RuntimeError):
    pass