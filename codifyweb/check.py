class Check:
    def __init__(self, check, check_type, result_column,
                 handler, vendor, frequency, sub_type):
        self.check = check
        self.check_type = check_type
        self.result_column = result_column
        self.handler = handler
        self.vendor = vendor
        self.frequency = frequency
        self.sub_type = sub_type

    def __str__(self):
        check_dict = {
            'check': self.check,
            'check_type': self.check_type,
            'result_column': self.result_column,
            'handler': self.handler,
            'check_vendor': self.vendor,
            'frequency': self.frequency,
            'sub_type' : self.sub_type
        }
        return str(check_dict)
