import json

import requests
from bson.objectid import ObjectId
from pymongo import ReturnDocument


class Paxos:
    # instance variables
    min_proposal_ids: dict
    replicas: list[str]
    base_url: str
    accepted_proposal_ids: dict
    accepted_proposal_values = dict
    _id = 'user_id'

    # static variables
    NOT_ACCEPTED = "not-accepted"
    ACCEPTED = "accepted"

    def __init__(self, replicas: list[str], base_url: str, db, min_proposal_ids: dict = None):
        if min_proposal_ids is None:
            self.min_proposal_ids = {}
        else:
            self.min_proposal_ids = min_proposal_ids
        self.replicas = replicas
        self.base_url = base_url
        self.db = db

    def proposer_prepare(self, proposal_value):
        payment_id: str = proposal_value[self._id]
        proposal_id = self.get_min_proposal_id(payment_id) + 1
        responses = []
        # TODO make this loop asynchronous
        for replica_url in self.replicas:
            # TODO check if port!= self.port
            r = requests.post(f'{replica_url}/prepare/', json=json.dumps(
                {'proposal_id': proposal_id, 'proposal_value': proposal_value}))
            if r.status_code == 200:
                responses.append(r.json())
        return self.proposer_accept(responses)

    def acceptor_prepare(self, proposal_id: int, proposal_value):
        user_id: str = proposal_value[self._id]
        min_proposal_id = self.get_min_proposal_id(user_id)
        if proposal_id > min_proposal_id:
            accepted_proposal_id = self.get_accepted_proposal_id(user_id)
            if accepted_proposal_id is not None:
                return json.dumps(
                    {'accepted_id': accepted_proposal_id, 'accepted_value': self.get_accepted_proposal_value(user_id)
                     }), 200
            self.set_accepted(user_id, proposal_id, proposal_value)
            return json.dumps({'accepted_id': proposal_id, 'accepted_value': proposal_value}), 200
        # TODO get accepted value here
        current_value = ""
        return current_value, 400

    def proposer_accept(self, vote_list: list):
        if len(vote_list) < len(self.nodes) // 2:
            return self.NOT_ACCAPTED
        max_id: int = -1
        value = None
        for vote in vote_list:
            if vote['accepted_id'] > max_id:
                max_id = vote['accepted_id']
                value = vote['accepted_value']

        accept_responses = 0
        for port in self.replicas:
            response = requests.post(f'{self.base_url}:{port}/accept', json=json.dumps(
                {'accepted_id': max_id, 'accepted_value': value}))
            if response.status_code == 200:
                accept_responses += 1

        # TODO handle post accepted phase
        if accept_responses > len(self.replicas) // 2:  # a Quorum is reached
            user_id: str = value[self._id]
            self.set_min_proposal_id(user_id, max_id)
            self.update_value(value)
        return self.ACCEPTED

    def acceptor_accept(self, accepted_id: int, proposal_value):
        user_id = proposal_value[self._id]
        accepted_proposal_id = self.get_accepted_proposal_id(user_id)
        if accepted_proposal_id is not None and accepted_proposal_id > accepted_id:
            return 'not accepted', 400
        self.update_value(proposal_value)
        self.set_min_proposal_id(user_id, accepted_id)
        return 'accepted', 200

    def set_min_proposal_id(self, user_id: str, proposal_id: int):
        # TODO add persistence for min_proposal_id
        self.min_proposal_ids[user_id] = proposal_id

    def get_min_proposal_id(self, user_id):
        if user_id in self.min_proposal_ids:
            return 0
        return self.min_proposal_ids[user_id]

    def set_accepted(self, user_id: str, proposal_id: int, proposal_value):
        self.accepted_proposal_ids[user_id] = proposal_id
        self.accepted_proposal_values[user_id] = proposal_value

    def get_accepted_proposal_id(self, user_id: str):
        if user_id not in self.accepted_proposal_ids:
            return None
        return self.accepted_proposal_ids[user_id]

    def get_accepted_proposal_value(self, user_id):
        assert user_id in self.accepted_proposal_values
        return self.accepted_proposal_values[user_id]

    def update_value(self, proposal_value):
        """
            Update value to data base
        """
        user = self.db.users.find_one_and_update(
            {'_id': ObjectId(proposal_value['user_id'])},
            {'$set': {'credit': proposal_value['credit']}},
            return_document=ReturnDocument.AFTER
        )
