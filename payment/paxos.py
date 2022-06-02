import json

import requests


class Paxos:
    min_proposal_ids: dict
    nodes_ports: list[str]
    base_url: str
    accepted_proposal_ids: dict
    accepted_proposal_values = dict

    def __init__(self, min_proposal_ids: dict, nodes: list[str], base_url: str, db):
        self.min_proposal_ids = min_proposal_ids
        self.nodes = nodes
        self.base_url = base_url
        self.db = db

    def proposer_prepare(self, proposal_value):
        payment_id: str = proposal_value['payment_id']
        proposal_id = self.get_min_proposal_id(payment_id) + 1
        responses = []
        # TODO make this loop asynchronous
        for port in self.nodes_ports:
            # TODO check if port!= self.port
            r = requests.post(f'{self.base_url}:{port}/prepare/', json=json.dumps(
                {'proposal_id': proposal_id, 'proposal_value': proposal_value}))
            if r.status_code == 200:
                responses.append(r.json())
        self.proposer_accept(responses)

    def acceptor_prepare(self, proposal_id: int, proposal_value):
        payment_id: str = proposal_value['payment_id']
        min_proposal_id = self.get_min_proposal_id(payment_id)
        if proposal_id > min_proposal_id:
            accepted_proposal_id = self.get_accepted_proposal_id(payment_id)
            if accepted_proposal_id is not None:
                return json.dumps(
                    {'accepted_id': accepted_proposal_id, 'accepted_value': self.get_accepted_proposal_value(payment_id)
                     }), 200
            self.set_accepted(payment_id, proposal_id, proposal_value)
            return json.dumps({'accepted_id': proposal_id, 'accepted_value': proposal_value}), 200
        # TODO get accepted value here
        current_value = ""
        return current_value, 400

    def proposer_accept(self, vote_list: list):
        if len(vote_list) < len(self.nodes) // 2:
            return
        max_id: int = -1
        value = None
        for vote in vote_list:
            if vote['accepted_id'] > max_id:
                max_id = vote['accepted_id']
                value = vote['accepted_value']

        accept_responses = 0
        for port in self.nodes_ports:
            response = requests.post(f'{self.base_url}:{port}/accept', json=json.dumps(
                {'accepted_id': max_id, 'accepted_value': value}))
            if response.status_code == 200:
                accept_responses += 1

        # TODO handle post accepted phase
        if accept_responses > len(self.nodes_ports) // 2:  # a Quorum is reached
            payment_id: str = value['payment_id']
            self.set_min_proposal_id(payment_id, max_id)
            self.update_value(value)

    def acceptor_accept(self, accepted_id: int, proposal_value):
        payment_id = proposal_value['payment_id']
        accepted_proposal_id = self.get_accepted_proposal_id(payment_id)
        if accepted_proposal_id is not None and accepted_proposal_id > accepted_id:
            return 'not accepted', 400
        self.update_value(proposal_value)
        self.set_min_proposal_id(payment_id, accepted_id)
        return 'accepted', 200

    def set_min_proposal_id(self, payment_id: str, proposal_id: int):
        # TODO add persistence for min_proposal_id
        self.min_proposal_ids[payment_id] = proposal_id

    def get_min_proposal_id(self, payment_id):
        if payment_id in self.min_proposal_ids:
            return 0
        return self.min_proposal_ids[payment_id]

    def set_accepted(self, payment_id: str, proposal_id: int, proposal_value):
        self.accepted_proposal_ids[payment_id] = proposal_id
        self.accepted_proposal_values[payment_id] = proposal_value

    def get_accepted_proposal_id(self, payment_id: str):
        if payment_id not in self.accepted_proposal_ids:
            return None
        return self.accepted_proposal_ids[payment_id]

    def get_accepted_proposal_value(self, payment_id):
        assert payment_id in self.accepted_proposal_values
        return self.accepted_proposal_values[payment_id]

    def update_value(self, proposal_value):
        # update value to data base
        pass
