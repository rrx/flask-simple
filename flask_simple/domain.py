import logging
log = logging.getLogger(__name__)

class Domain:
    def __init__(self, client, name):
        assert(client)
        assert(name)
        self.client = client
        self.name = name

    def select(self, **kwargs):
        paginator = self.client.get_paginator('select')
        fields = []
        for k, v in kwargs.items():
            fields.append("%s='%s'" % (k, v))
        selects = " and ".join(fields)

        expression = "select * from %s where %s" % (self.name, selects)

        results = paginator.paginate(
            SelectExpression=expression,
            ConsistentRead=True
        )
        for data in results:
            for v in data.get('Items', []):
                item = {
                    'id': v['Name']
                }
                for attr in v.get('Attributes', []):
                    item[attr['Name']] = attr['Value']
                yield item

    def get_consistent(self, idValue, attributes=None):
        args = dict(
            DomainName=self.name,
            ItemName=idValue,
            ConsistentRead=True
        )
        if attributes:
            args['AttributeNames'] = list(attributes)

        result = self.client.get_attributes(**args)
        out = {}
        for attr in result.get('Attributes', []):
            out[attr['Name']] = attr['Value']
        return out

    def update(self, idValue, data):
        attributes = []
        for k, v in data.items():
            attributes.append({
                    'Name': k,
                    'Value': v,
                    'Replace': True
            })

        log.info('update %s %s %s', self.name, idValue, attributes)
        result = self.client.put_attributes(
            DomainName=self.name,
            ItemName=idValue,
            Attributes=attributes
        )

        # XXX: no error handling yet, we should check the result

    def remove(self, idValue):
        result = self.client.delete_attributes(
            DomainName=self.name,
            ItemName=idValue
        )
