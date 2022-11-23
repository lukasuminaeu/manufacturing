# -*- coding: utf-8 -*-
from odoo import models, fields, api
from operator import attrgetter
import psycopg2
import time
from odoo.exceptions import UserError, ValidationError, Warning

import logging
_logger = logging.getLogger(__name__)

class RetryFunction(models.AbstractModel):
    _inherit = 'base'

    def retry_on_db_failure(self, method=False, parent=False, times_to_retry=200, method_props=False):
        """This function will try to reinitiate function on failed sql transaction
            because of serialization, deadlock or failed transaction error.
        Args:
            method (string, optional): _description_. Defaults to False.
            method_props (bool, optional): _description_. Defaults to False.
            times_to_retry (int, optional): _description_. Defaults to 50.
        """        
        res = False
        _logger.info('Initiated serialization retry function')
        try:
            #Function below to execute function that will initiate serialization error.
            # self._cr.execute("""
            #     DO $$BEGIN RAISE EXCEPTION 'Serialization error' USING ERRCODE = 'serialization_failure'; END $$;
            # """)

            # #Try to call a parent method
            res = getattr(parent, method)()

        except (
            psycopg2.errors.SerializationFailure, 
            psycopg2.errors.InFailedSqlTransaction,
            psycopg2.errors.DeadlockDetected
        ) as e:
            #At serialization failure error execute following code block
            if not 'failure_retry_index' in self._context:
                self.env.context = dict(self.env.context)
                failure_retry_index = 1
                self.env.context.update({'failure_retry_index': failure_retry_index})
            else:
                failure_retry_index = self._context['failure_retry_index'] + 1
            if failure_retry_index < times_to_retry:
                self._cr.rollback()
                #Retry after 0.5 second
                time.sleep(0.5)
                # self.with_context(failure_retry_index=failure_retry_index).action_next()
                _logger.info(f"Retrying {failure_retry_index} times. Method '{method}'")
                res = getattr(parent.with_context(failure_retry_index=failure_retry_index), method)()
            else:
                raise UserError(e)
        
        # except psycopg2.errors.InFailedSqlTransaction as e:
        #     print('zzz111')
        #     #At serialization failure error execute following code block
        #     if not 'failure_retry_index' in self._context:
        #         self.env.context = dict(self.env.context)
        #         failure_retry_index = 1
        #         self.env.context.update({'failure_retry_index': failure_retry_index})
        #     else:
        #         failure_retry_index = self._context['failure_retry_index'] + 1
        #     if failure_retry_index < times_to_retry:
        #         self._cr.rollback()
        #         #Retry after 0.5 second
        #         time.sleep(0.5)
        #         # self.with_context(failure_retry_index=failure_retry_index).action_next()
        #         _logger.info(f"Retrying {failure_retry_index} times. Method '{method}'")
        #         res = getattr(parent.with_context(failure_retry_index=failure_retry_index), method)()
        #     else:
        #         raise UserError(psycopg2.errors.InFailedSqlTransaction)
        # except psycopg2.errors.DeadlockDetected as e:
        #     print('qwe123')
        #     print(e)
        #     print('zzz111')
        #     #At serialization failure error execute following code block
        #     if not 'failure_retry_index' in self._context:
        #         self.env.context = dict(self.env.context)
        #         failure_retry_index = 1
        #         self.env.context.update({'failure_retry_index': failure_retry_index})
        #     else:
        #         failure_retry_index = self._context['failure_retry_index'] + 1
        #     if failure_retry_index < times_to_retry:
        #         self._cr.rollback()
        #         #Retry after 0.5 second
        #         time.sleep(0.5)
        #         # self.with_context(failure_retry_index=failure_retry_index).action_next()
        #         _logger.info(f"Retrying {failure_retry_index} times. Method '{method}'")
        #         res = getattr(parent.with_context(failure_retry_index=failure_retry_index), method)()
        #     else:
        #         raise UserError(psycopg2.errors.DeadlockDetected)
        
        # except Exception as e:
        #     print('zxczxc123')
        #     print(e)
        #     raise Warning(e)

        return res
        # self.with_context(failure_retry_index=failure_retry_index).action_next()
    

