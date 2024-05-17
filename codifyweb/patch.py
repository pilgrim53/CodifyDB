class Patch:
    def __init__(self, inventory_id, hostname, instance_name, vendor, sched_date_time,
                 APPLY, rollbacks, oneoffs, scp_copy, ticket, sw_release):
        self.id = inventory_id
        self.host = hostname
        self.instance = instance_name
        self.vendor = vendor
        self.sched = sched_date_time
        self.apply = APPLY
        self.rollbacks = rollbacks
        self.oneoffs = oneoffs
        self.scp_copy = scp_copy
        self.ticket = ticket
        self.sw_release = sw_release

    def __str__(self):
        patch_dict = {
            'id': self.id,
            'host': self.host,
            'instance': self.instance,
            'vendor': self.vendor,
            'sched': self.sched,
            'apply': self.apply,
            'rollbacks': self.rollbacks,
            'oneoffs': self.oneoffs,
            'scp_copy': self.scp_copy,
            'ticket' : self.ticket,
            'sw_release' : self.sw_release
        }
        return str(patch_dict)

