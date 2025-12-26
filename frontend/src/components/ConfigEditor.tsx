'use client';

import { useState } from 'react';
import { Settings, Plus, Trash2, Download, Upload, RotateCcw, ChevronDown, ChevronRight, Edit2, X, Check } from 'lucide-react';
import { ProductInfo } from '@/config/productConfig';

interface ConfigEditorProps {
  productConfig: Record<string, ProductInfo>;
  onUpdate: (code: string, info: ProductInfo) => void;
  onDelete: (code: string) => void;
  onReset: () => void;
  onImport: (json: string) => boolean;
  onExport: () => string;
}

export default function ConfigEditor({
  productConfig,
  onUpdate,
  onDelete,
  onReset,
  onImport,
  onExport,
}: ConfigEditorProps) {
  const [isExpanded, setIsExpanded] = useState(false);
  const [editingCode, setEditingCode] = useState<string | null>(null);
  const [editForm, setEditForm] = useState<ProductInfo | null>(null);
  const [newCode, setNewCode] = useState('');
  const [newQty, setNewQty] = useState('1');

  const handleExport = () => {
    const json = onExport();
    const blob = new Blob([json], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'product_config.json';
    a.click();
    URL.revokeObjectURL(url);
  };

  const handleImport = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      const reader = new FileReader();
      reader.onload = (event) => {
        const content = event.target?.result as string;
        const success = onImport(content);
        if (!success) {
          alert('匯入失敗：JSON 格式錯誤');
        }
      };
      reader.readAsText(file);
    }
  };

  const handleAddProduct = () => {
    if (!newCode.trim()) return;
    onUpdate(newCode.trim(), {
      qty: parseInt(newQty) || 1,
      mixx_name: [],
      c2c_code: [],
      c2c_name: [],
      aoshi_name: [],
    });
    setNewCode('');
    setNewQty('1');
  };

  const startEdit = (code: string, info: ProductInfo) => {
    setEditingCode(code);
    setEditForm({ ...info });
  };

  const cancelEdit = () => {
    setEditingCode(null);
    setEditForm(null);
  };

  const saveEdit = () => {
    if (editingCode && editForm) {
      onUpdate(editingCode, editForm);
      cancelEdit();
    }
  };

  const updateEditField = (field: keyof ProductInfo, value: string) => {
    if (!editForm) return;
    if (field === 'qty') {
      setEditForm({ ...editForm, qty: parseInt(value) || 0 });
    } else {
      setEditForm({
        ...editForm,
        [field]: value.split('\n').map(s => s.trim()).filter(s => s),
      });
    }
  };

  return (
    <div className="card">
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full p-4 flex items-center justify-between hover:bg-gray-50 transition-colors"
      >
        <div className="flex items-center gap-3">
          <Settings className="w-5 h-5 text-gray-500" />
          <span className="font-medium text-gray-800">產品配置管理</span>
          <span className="text-sm text-gray-500">
            ({Object.keys(productConfig).length} 項產品)
          </span>
        </div>
        {isExpanded ? (
          <ChevronDown className="w-5 h-5 text-gray-400" />
        ) : (
          <ChevronRight className="w-5 h-5 text-gray-400" />
        )}
      </button>

      {isExpanded && (
        <div className="border-t border-gray-100">
          <div className="p-4 bg-gray-50 flex flex-wrap gap-2">
            <button onClick={handleExport} className="btn-secondary text-sm py-2 px-4 flex items-center gap-2">
              <Download className="w-4 h-4" />
              匯出配置
            </button>
            <label className="btn-secondary text-sm py-2 px-4 flex items-center gap-2 cursor-pointer">
              <Upload className="w-4 h-4" />
              匯入配置
              <input type="file" accept=".json" onChange={handleImport} className="hidden" />
            </label>
            <button onClick={onReset} className="btn-secondary text-sm py-2 px-4 flex items-center gap-2 text-red-600 hover:text-red-700">
              <RotateCcw className="w-4 h-4" />
              重置為預設
            </button>
          </div>

          <div className="p-4 border-t border-gray-100">
            <div className="flex gap-2 mb-4">
              <input
                type="text"
                value={newCode}
                onChange={(e) => setNewCode(e.target.value)}
                placeholder="產品編號"
                className="flex-1 px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-green-500"
              />
              <input
                type="number"
                value={newQty}
                onChange={(e) => setNewQty(e.target.value)}
                placeholder="數量"
                className="w-20 px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-green-500"
              />
              <button onClick={handleAddProduct} className="btn-primary py-2 px-4 flex items-center gap-2">
                <Plus className="w-4 h-4" />
                新增
              </button>
            </div>

            <div className="max-h-[500px] overflow-y-auto space-y-2">
              {Object.entries(productConfig).map(([code, info]) => (
                <div key={code} className="border border-gray-200 rounded-lg p-3 hover:bg-gray-50">
                  {editingCode === code && editForm ? (
                    <div className="space-y-3">
                      <div className="flex justify-between items-center">
                        <span className="font-mono text-sm font-semibold text-green-600">{code}</span>
                        <div className="flex gap-1">
                          <button onClick={saveEdit} className="p-1.5 text-green-600 hover:bg-green-50 rounded">
                            <Check className="w-4 h-4" />
                          </button>
                          <button onClick={cancelEdit} className="p-1.5 text-gray-500 hover:bg-gray-100 rounded">
                            <X className="w-4 h-4" />
                          </button>
                        </div>
                      </div>
                      <div className="grid grid-cols-2 gap-3">
                        <div>
                          <label className="text-xs text-gray-500 block mb-1">數量 (qty)</label>
                          <input
                            type="number"
                            value={editForm.qty}
                            onChange={(e) => updateEditField('qty', e.target.value)}
                            className="w-full px-2 py-1 text-sm border border-gray-300 rounded"
                          />
                        </div>
                      </div>
                      <div>
                        <label className="text-xs text-gray-500 block mb-1">MIXX 名稱 (每行一個)</label>
                        <textarea
                          value={editForm.mixx_name.join('\n')}
                          onChange={(e) => updateEditField('mixx_name', e.target.value)}
                          rows={2}
                          className="w-full px-2 py-1 text-sm border border-gray-300 rounded font-mono"
                        />
                      </div>
                      <div>
                        <label className="text-xs text-gray-500 block mb-1">C2C 編號 (每行一個)</label>
                        <textarea
                          value={editForm.c2c_code.join('\n')}
                          onChange={(e) => updateEditField('c2c_code', e.target.value)}
                          rows={2}
                          className="w-full px-2 py-1 text-sm border border-gray-300 rounded font-mono"
                        />
                      </div>
                      <div>
                        <label className="text-xs text-gray-500 block mb-1">C2C 名稱 (每行一個)</label>
                        <textarea
                          value={editForm.c2c_name.join('\n')}
                          onChange={(e) => updateEditField('c2c_name', e.target.value)}
                          rows={2}
                          className="w-full px-2 py-1 text-sm border border-gray-300 rounded font-mono"
                        />
                      </div>
                      <div>
                        <label className="text-xs text-gray-500 block mb-1">奧世國際 名稱 (每行一個)</label>
                        <textarea
                          value={(editForm.aoshi_name || []).join('\n')}
                          onChange={(e) => updateEditField('aoshi_name', e.target.value)}
                          rows={2}
                          className="w-full px-2 py-1 text-sm border border-gray-300 rounded font-mono"
                        />
                      </div>
                    </div>
                  ) : (
                    <div>
                      <div className="flex justify-between items-start mb-2">
                        <div>
                          <span className="font-mono text-sm font-semibold text-gray-800">{code}</span>
                          <span className="ml-2 text-xs bg-blue-100 text-blue-700 px-2 py-0.5 rounded">
                            qty: {info.qty}
                          </span>
                        </div>
                        <div className="flex gap-1">
                          <button
                            onClick={() => startEdit(code, info)}
                            className="p-1.5 text-gray-500 hover:bg-gray-100 rounded"
                          >
                            <Edit2 className="w-4 h-4" />
                          </button>
                          <button
                            onClick={() => onDelete(code)}
                            className="p-1.5 text-red-500 hover:bg-red-50 rounded"
                          >
                            <Trash2 className="w-4 h-4" />
                          </button>
                        </div>
                      </div>
                      <div className="grid grid-cols-2 gap-2 text-xs">
                        {info.mixx_name.length > 0 && (
                          <div>
                            <span className="text-gray-400">MIXX:</span>
                            <div className="text-gray-600 truncate">{info.mixx_name.join(', ')}</div>
                          </div>
                        )}
                        {info.c2c_code.length > 0 && (
                          <div>
                            <span className="text-gray-400">C2C Code:</span>
                            <div className="text-gray-600 font-mono truncate">{info.c2c_code.join(', ')}</div>
                          </div>
                        )}
                        {info.c2c_name.length > 0 && (
                          <div>
                            <span className="text-gray-400">C2C Name:</span>
                            <div className="text-gray-600 truncate">{info.c2c_name.join(', ')}</div>
                          </div>
                        )}
                        {info.aoshi_name && info.aoshi_name.length > 0 && (
                          <div>
                            <span className="text-gray-400">奧世:</span>
                            <div className="text-gray-600 truncate">{info.aoshi_name.join(', ')}</div>
                          </div>
                        )}
                      </div>
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
