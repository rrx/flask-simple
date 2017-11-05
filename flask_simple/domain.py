class Domain:
    def __init__(self, client, name):
        assert(client)
        assert(name)
        self.client = client
        self.name = name

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
        print('delete result', result)
