import weakref
from collections import deque
from typing import Any, Deque, Dict, Optional


class IdManager:
    def __init__(self) -> None:
        self.max_id: int = 2**31 - 1
        self.next_id: int = 0

        self.released_ids: Deque[int] = deque()
        self.object_to_id: weakref.WeakKeyDictionary[Any, int] = weakref.WeakKeyDictionary()
        self.id_to_object: weakref.WeakValueDictionary[int, Any] = weakref.WeakValueDictionary()
        self._finalizers: Dict[int, weakref.ref[Any]] = {}

    def get_id(self, obj: Any) -> int:
        if obj in self.object_to_id:
            return self.object_to_id[obj]

        if self.released_ids:
            obj_id: int = self.released_ids.popleft()
        else:
            if self.next_id > self.max_id:
                raise RuntimeError("Keine IDs mehr verfügbar!")
            obj_id = self.next_id
            self.next_id += 1

        self.object_to_id[obj] = obj_id
        self.id_to_object[obj_id] = obj

        def _on_object_gc(ref: "weakref.ReferenceType[Any]", id_: int = obj_id) -> None:
            self.release_id(id_)

        ref = weakref.ref(obj, _on_object_gc)
        self._finalizers[obj_id] = ref

        return obj_id

    def release_id(self, obj_id: int) -> None:
        if obj_id in self.id_to_object:
            del self.id_to_object[obj_id]

        if obj_id in self._finalizers:
            del self._finalizers[obj_id]

        self.released_ids.append(obj_id)

    def release_obj(self, obj: Any) -> None:
        if obj in self.object_to_id:
            obj_id: int = self.object_to_id.pop(obj)

            if obj_id in self.id_to_object:
                del self.id_to_object[obj_id]

            if obj_id in self._finalizers:
                del self._finalizers[obj_id]

            self.released_ids.append(obj_id)

    def get_object(self, obj_id: int) -> Optional[Any]:
        return self.id_to_object.get(obj_id)

    def get_id_from_obj(self, obj: Any) -> Optional[int]:
        return self.object_to_id.get(obj)
