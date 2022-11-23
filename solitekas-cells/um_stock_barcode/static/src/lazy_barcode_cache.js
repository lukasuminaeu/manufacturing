/** @odoo-module **/
import LazyBarcodeCache from '@stock_barcode/lazy_barcode_cache';
import {patch} from 'web.utils';

patch(LazyBarcodeCache.prototype, 'um_stock_barcode/lazy_barcode_cache.js', {
    /**
     * @override
     */
    async getRecordByBarcode(barcode, model = false, onlyInCache = false, filters = {}) {	
        if (model) {	
            if (!this.dbBarcodeCache.hasOwnProperty(model)) {	
                throw new Error(`Model ${model} doesn't exist in the cache`);	
            }	
            if (!this.dbBarcodeCache[model].hasOwnProperty(barcode)) {	
                if (onlyInCache) {	
                    return null;	
                }	
                await this._getMissingRecord(barcode, model);	
                return await this.getRecordByBarcode(barcode, model, true);	
            }	
            const id = this.dbBarcodeCache[model][barcode][0];	
            return this.getRecord(model, id);	
        } else {	
            const result = new Map();	
            // Returns object {model: record} of possible record.	
            const models = Object.keys(this.dbBarcodeCache);	
            for (const model of models) {	
                if (this.dbBarcodeCache[model].hasOwnProperty(barcode)) {	
                    const ids = this.dbBarcodeCache[model][barcode];	
                    for (const id of ids) {	
                        const record = this.dbIdCache[model][id];	
                        result.set(model, JSON.parse(JSON.stringify(record)));	
                        if (filters[model]) {	
                            let pass = true;	
                            const fields = Object.keys(filters[model]);	
                            for (const field of fields) {	
                                if (record[field] != filters[model][field]) {	
                                    pass = false;	
                                    break;	
                                }	
                            }	
                            if (pass) {	
                                break;	
                            }	
                        }	
                    }	
                }	
            }	
            if (result.size < 1) {	
                if (onlyInCache) {	
                    return result;	
                }	
                await this._getMissingRecord(barcode, model, filters);	
                return await this.getRecordByBarcode(barcode, model, true);	
            }	
            return result;	
        }	
    },

    /**
     * @override
    */
    async _getMissingRecord(barcode, model, filters) {	
        const missCache = this.missingBarcode;	
        const params = { barcode, model_name: model };	
        // Check if we already try to fetch this missing record.	
        if (missCache.has(barcode) || missCache.has(`${barcode}_${model}`)) {	
            return false;	
        }	
        // Creates and passes a domain if some filters are provided.	
        if (filters) {	
            const domainsByModel = {};	
            for (const filter of Object.entries(filters)) {	
                const modelName = filter[0];	
                const filtersByField = filter[1];	
                domainsByModel[modelName] = [];	
                for (const filterByField of Object.entries(filtersByField)) {	
                    domainsByModel[modelName].push([filterByField[0], '=', filterByField[1]]);	
                }	
            }	
            params.domains_by_model = domainsByModel;	
        }	
        const result = await this.rpc('/stock_barcode/get_specific_barcode_data', params);	
        this.setCache(result);	
        // Set the missing cache	
        const keyCache = (model && `${barcode}_${model}`) || barcode;	
        missCache.add(keyCache);	
    }
    

});
