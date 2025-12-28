import { useState, useEffect } from 'react';
import { settingsApi, AllMappings } from '@/lib/api/settings';
import { Plus, Trash2, Save, X, RotateCcw, Loader2 } from 'lucide-react';

const FIELD_LABELS: Record<string, string> = {
    order_id: "訂單編號 (Order ID)",
    order_date: "訂單日期 (Date)",
    receiver_name: "收件人姓名 (Name)",
    receiver_phone: "收件人電話 (Phone)",
    receiver_address: "收件人地址 (Address)",
    delivery_method: "送貨方式 (Delivery)",
    store_name: "門市名稱 (Store)",
    product_code: "商品編號 (Code)",
    product_name: "商品名稱 (Product Name)",
    quantity: "數量 (Qty)",
    order_mark: "訂單備註 (Mark)",
    arrival_time: "到貨時段 (Arrival)"
};

export default function MappingEditor() {
    const [mappings, setMappings] = useState<AllMappings>({});
    const [loading, setLoading] = useState(true);
    const [selectedPlatform, setSelectedPlatform] = useState<string>('shopline');
    const [unsavedChanges, setUnsavedChanges] = useState(false);

    // Local edit state
    const [newAlias, setNewAlias] = useState('');
    const [addingToField, setAddingToField] = useState<string | null>(null);

    useEffect(() => {
        loadMappings();
    }, []);

    const loadMappings = async () => {
        try {
            setLoading(true);
            const data = await settingsApi.getAllMappings();
            setMappings(data);
            setUnsavedChanges(false);
        } catch (err) {
            console.error(err);
            alert('無法載入設定');
        } finally {
            setLoading(false);
        }
    };

    const handleSave = async () => {
        try {
            await settingsApi.updateMapping(selectedPlatform, mappings[selectedPlatform]);
            setUnsavedChanges(false);
            alert('儲存成功');
        } catch (err) {
            alert('儲存失敗');
        }
    };

    const currentMapping = mappings[selectedPlatform] || {};

    const addAlias = (field: string) => {
        if (!newAlias.trim()) return;

        const updatedList = [...(currentMapping[field] || []), newAlias.trim()];

        setMappings(prev => ({
            ...prev,
            [selectedPlatform]: {
                ...prev[selectedPlatform],
                [field]: updatedList
            }
        }));

        setNewAlias('');
        setAddingToField(null);
        setUnsavedChanges(true);
    };

    const removeAlias = (field: string, index: number) => {
        const updatedList = [...(currentMapping[field] || [])];
        updatedList.splice(index, 1);

        setMappings(prev => ({
            ...prev,
            [selectedPlatform]: {
                ...prev[selectedPlatform],
                [field]: updatedList
            }
        }));
        setUnsavedChanges(true);
    };

    if (loading) return <div className="p-8 flex justify-center"><Loader2 className="animate-spin text-green-500" /></div>;

    return (
        <div className="space-y-6">
            <div className="flex justify-between items-center bg-gray-50 p-4 rounded-lg">
                <div className="flex items-center gap-4">
                    <label className="font-semibold text-gray-700">選擇平台:</label>
                    <select
                        value={selectedPlatform}
                        onChange={(e) => setSelectedPlatform(e.target.value)}
                        className="px-3 py-2 border rounded-md bg-white focus:ring-2 focus:ring-green-500"
                    >
                        {Object.keys(mappings).map(p => (
                            <option key={p} value={p}>{p.toUpperCase()}</option>
                        ))}
                    </select>
                </div>

                <div className="flex gap-2">
                    <button
                        onClick={loadMappings}
                        className="flex items-center gap-2 px-3 py-2 text-gray-600 hover:bg-gray-200 rounded"
                    >
                        <RotateCcw className="w-4 h-4" /> 重置
                    </button>
                    <button
                        onClick={handleSave}
                        disabled={!unsavedChanges}
                        className={`flex items-center gap-2 px-4 py-2 rounded text-white ${unsavedChanges ? 'bg-green-600 hover:bg-green-700 shadow-md' : 'bg-gray-300 cursor-not-allowed'}`}
                    >
                        <Save className="w-4 h-4" /> 儲存變更
                    </button>
                </div>
            </div>

            <div className="grid gap-6">
                {Object.keys(currentMapping).map(field => (
                    <div key={field} className="border p-4 rounded-lg bg-white">
                        <div className="flex justify-between items-start mb-2">
                            <div>
                                <h4 className="font-bold text-gray-800">{FIELD_LABELS[field] || field}</h4>
                                <span className="text-xs text-gray-400 font-mono">{field}</span>
                            </div>
                            <button
                                onClick={() => setAddingToField(field)}
                                className="text-green-600 hover:bg-green-50 p-1 rounded"
                            >
                                <Plus className="w-4 h-4" />
                            </button>
                        </div>

                        <div className="flex flex-wrap gap-2">
                            {currentMapping[field]?.map((alias, idx) => (
                                <span key={idx} className="inline-flex items-center gap-1 px-2 py-1 bg-blue-50 text-blue-700 border border-blue-200 rounded text-sm">
                                    {alias}
                                    <button onClick={() => removeAlias(field, idx)} className="hover:text-red-500">
                                        <X className="w-3 h-3" />
                                    </button>
                                </span>
                            ))}
                            {(!currentMapping[field] || currentMapping[field].length === 0) && (
                                <span className="text-gray-400 text-sm italic">無對應欄位</span>
                            )}
                        </div>

                        {/* Add Input */}
                        {addingToField === field && (
                            <div className="mt-3 flex gap-2">
                                <input
                                    autoFocus
                                    className="flex-1 px-2 py-1 border rounded text-sm"
                                    placeholder="輸入 Excel 欄位名稱"
                                    value={newAlias}
                                    onChange={(e) => setNewAlias(e.target.value)}
                                    onKeyDown={(e) => e.key === 'Enter' && addAlias(field)}
                                />
                                <button onClick={() => addAlias(field)} className="px-3 py-1 bg-green-600 text-white rounded text-sm">確定</button>
                                <button onClick={() => { setAddingToField(null); setNewAlias(''); }} className="px-2 text-gray-500">取消</button>
                            </div>
                        )}
                    </div>
                ))}
            </div>

            <div className="bg-yellow-50 p-4 rounded text-sm text-yellow-800">
                <p><strong>💡 提示：</strong> 這些設定決定了系統如何讀取您的 Excel 檔案。如果您上傳的檔案欄位名稱有變 (例如「收件人」變成了「顧客姓名」)，請在此處新增對應，系統即可正確識別，無須修改程式碼。</p>
            </div>
        </div>
    );
}
