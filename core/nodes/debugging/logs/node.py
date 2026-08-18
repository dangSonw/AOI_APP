import logging

from core.nodes.models import NodeInputs, NodeOutputs, NodeParameters, NodeUse


NODE_ID = 'logs'
USE = NodeUse.DEBUG
INPUT_KEYS = ()
OUTPUT_KEYS = ()

LOGGER = logging.getLogger('aoi.workflow.logs')
DESTINATIONS = {'popup', 'terminal', 'file'}
LEVELS = {
    'info': logging.INFO,
    'warning': logging.WARNING,
    'error': logging.ERROR,
}


def execute(_: NodeInputs, parameters: NodeParameters) -> NodeOutputs:
    destination = str(parameters['destination'])
    level = str(parameters['level'])
    message = str(parameters['message']).strip()
    if destination not in DESTINATIONS:
        raise ValueError('Log destination must be popup, terminal, or file.')
    if level not in LEVELS:
        raise ValueError('Log level must be info, warning, or error.')
    if not message or len(message) > 1000:
        raise ValueError('Log message must contain between 1 and 1000 characters.')

    if destination == 'terminal':
        LOGGER.log(LEVELS[level], message)
        return {}
    return {'__log__': {'destination': destination, 'level': level, 'message': message}}