from dataclasses import dataclass

from datetime import datetime, timedelta
from typing import List, Mapping

from bson import ObjectId
from fastapi import HTTPException

from classes.database_provider import DatabaseProvider
from classes.open_route_service import OpenRouteService
from classes.package_status import PackageStatus
from classes.raw_route import RawRoute
from classes.package import Package
from classes.transport import Transport


@dataclass
class Route:
    cities: List[str]
    transport: str
    schedule: List[datetime]
    current_position: int
    packages: List[Package]
    current_weight: float
    id: ObjectId = None

    @staticmethod
    def get_best_routes(origin: str, destination: str, timestamp: datetime) -> List['Route']:
        documents = list(DatabaseProvider.routes().aggregate([
            {
                '$match': {
                    'cities': {'$all': [origin, destination]},
                    'schedule': {'$gt': timestamp}
                },
            },
            {
                '$project': {
                    'office_index': {'$indexOfArray': ['$cities', origin]},
                    'destination_index': {'$indexOfArray': ['$cities', destination]},
                    'transport': 1,
                    'coordinates': 1,
                    'schedule': 1,
                    'current_position': 1,
                    'packages': 1,
                    'current_weight': 1,
                    'cities': 1,
                }
            },
            {'$match': {'$expr': {'$lt': ['$office_index', '$destination_index']}}},
            {'$match': {'$expr': {'$lte': ['$office_index', '$current_position']}}},
            {'$sort': {'schedule': 1}}
        ]))
        return [Route.from_dict(document) for document in documents]

    @classmethod
    def from_raw_route(cls, raw_route: RawRoute):
        data = OpenRouteService.get_route_data(raw_route.cities)
        schedule = [raw_route.start]
        for duration in data['durations']:
            schedule.append(schedule[-1] + timedelta(seconds=duration))
        transport = DatabaseProvider.transports().find_one({'_id': raw_route.transport})
        if transport is None:
            raise HTTPException(status_code=404, detail='Transport not found')
        return cls(cities=raw_route.cities, transport=raw_route.transport, schedule=schedule, current_position=0, packages=[], current_weight=0)

    @classmethod
    def from_dict(cls, data: Mapping):
        return cls(
            id=data['_id'],
            cities=data['cities'],
            transport=data['transport'],
            schedule=data['schedule'],
            current_position=data['current_position'],
            packages=[Package.from_dict(package) for package in data['packages']],
            current_weight=data['current_weight']
        )

    def add_package(self, package: Package):
        self.packages.append(package)
        transport = Transport.from_dict(DatabaseProvider.transports().find_one({'_id': self.transport}))
        if transport.max_weight < self.current_weight + package.weight:
            raise HTTPException(status_code=406, detail='Package is too heavy')
        self.current_weight += package.weight
        DatabaseProvider.routes().update_one({'_id': self.id}, {'$push': {'packages': package.to_dict()}, '$set': {'current_weight': self.current_weight}})

    def increment_position(self):
        if self.current_position >= len(self.cities) - 1:
            raise HTTPException(status_code=406, detail='Current position is last city')
        self.current_position += 1
        if self.current_position == len(self.cities) - 1 and len(self.packages) > 0:
            DatabaseProvider.routes().update_one({'_id': self.id}, {'$set': {'packages.status': PackageStatus.WaitingReceiver}})
        DatabaseProvider.routes().update_one({'_id': self.id}, {'$inc': {'current_position': 1}})

    def to_dict(self):
        dict_val = {
            'cities': self.cities,
            'transport': self.transport,
            'current_position': self.current_position,
            'schedule': self.schedule,
            'packages': [package.to_dict() for package in self.packages],
            'current_weight': self.current_weight,
        }
        if self.id:
            dict_val['_id'] = str(self.id)
        return dict_val
