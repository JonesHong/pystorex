"""
基於 PyStoreX 的 Reducer 定義模組。

此模組提供建立和管理 Reducer 的功能。Reducers 是純函數，
負責根據接收到的 Action 將當前狀態轉換為新狀態。
"""

from typing import Dict, Any, Callable, Union, Tuple, Optional, overload, cast
from .actions import Action
from .types import (
    S, P, ActionHandler, HandlerMap, ReducerFunction, 
    Reducer as ReducerProtocol
)

# 使用類型模組中定義的 ReducerFunction 類型
Reducer = ReducerFunction


def create_reducer(initial_state: S, *handlers: Union[Tuple[str, ActionHandler], Dict[str, ActionHandler]]) -> ReducerFunction[S]:
    """
    創建一個 reducer 函式，用於處理狀態變更。

    Args:
        initial_state: 初始狀態。
        *handlers: 一系列 (action_type, handler_fn) 元組或使用 on 函式創建的處理器。

    Returns:
        一個 reducer 函式，根據 action 的類型執行對應的處理邏輯。
        
    範例:
        >>> # 創建一個計數器 reducer
        >>> increment = create_action("[Counter] Increment")
        >>> decrement = create_action("[Counter] Decrement")
        >>> reset = create_action("[Counter] Reset")
        >>> 
        >>> counter_reducer = create_reducer(
        ...     0,  # 初始狀態
        ...     on(increment, lambda state, action: state + 1),
        ...     on(decrement, lambda state, action: state - 1),
        ...     on(reset, lambda state, action: 0)
        ... )
    """
    action_handlers: HandlerMap = {}  # 儲存 action 類型與處理函式的對應關係
    
    for handler in handlers:
        if isinstance(handler, tuple) and len(handler) == 2:
            # 如果 handler 是元組，則解構為 action 類型與處理函式
            action_type, handler_fn = handler
            action_handlers[action_type] = handler_fn
        else:
            # 如果 handler 是字典，則直接更新到 action_handlers
            action_handlers.update(cast(Dict[str, ActionHandler], handler))
    
    def reducer(state: S = initial_state, action: Optional[Action[Any]] = None) -> S:
        """
        Reducer 函式，根據 action 處理狀態變更。

        Args:
            state: 當前狀態，默認為初始狀態。
            action: 要處理的 action，默認為 None。

        Returns:
            新的狀態，如果沒有對應的處理器則返回原狀態。
        """
        if action is None:
            return state  # 如果沒有 action，返回當前狀態
            
        handler = action_handlers.get(action.type)  # 根據 action 類型查找處理函式
        if handler:
            return handler(state, action)  # 執行處理函式
        return state  # 如果沒有對應處理函式，返回原狀態
    
    # 設置 reducer 的初始狀態和處理器映射
    reducer.initial_state = initial_state  # type: ignore
    reducer.handlers = action_handlers  # type: ignore
    
    return reducer


@overload
def on(action_creator: Callable[..., Action[P]], handler: Callable[[S, Action[P]], S]) -> Dict[str, ActionHandler]: ...

@overload
def on(action_type: str, handler: Callable[[S, Action[Any]], S]) -> Dict[str, ActionHandler]: ...

def on(action_creator_or_type: Union[Callable[..., Action[Any]], str], 
       handler: Callable[[S, Action[Any]], S]) -> Dict[str, ActionHandler]:
    """
    創建一個 action 類型與處理函式的映射。

    Args:
        action_creator_or_type: Action 創建器函式或 Action 類型字串。
        handler: 處理該 Action 的函式，接收 (state, action) 並返回新狀態。

    Returns:
        一個包含 {action_type: handler} 的字典。
        
    範例:
        >>> # 使用 action creator
        >>> increment = create_action("[Counter] Increment")
        >>> on(increment, lambda state, action: state + 1)
        >>> 
        >>> # 使用 action type 字串
        >>> on("[Counter] Increment", lambda state, action: state + 1)
    """
    if callable(action_creator_or_type) and hasattr(action_creator_or_type, 'type'):
        # 如果是 action 創建器函式，則提取其類型
        action_type = action_creator_or_type.type
    else:
        # 否則直接將其轉為字串作為類型
        action_type = str(action_creator_or_type)
    
    return {action_type: handler}  # 返回 action 類型與處理函式的映射


class ReducerManager:
    """
    管理應用中的所有 reducers，類似於 NgRx 的 MetaReducer。

    Attributes:
        _feature_reducers: 儲存每個功能模組的 reducer。
        _state: 儲存最新的整個 root state。
    """
    def __init__(self) -> None:
        """
        初始化 ReducerManager，創建空的 reducers 和狀態儲存。
        """
        self._feature_reducers: Dict[str, ReducerFunction] = {}  # 儲存功能模組的 reducers
        self._state: Dict[str, Any] = {}  # 儲存最新的 root state

    def add_reducer(self, feature_key: str, reducer: ReducerFunction) -> None:
        """
        添加一個 reducer 到指定的功能模組。

        Args:
            feature_key: 功能模組的鍵。
            reducer: 要添加的 reducer 函式。
        """
        self._feature_reducers[feature_key] = reducer
        self._state[feature_key] = reducer.initial_state  # type: ignore  # 初始化該功能模組的狀態

    def add_reducers(self, reducers: Dict[str, ReducerFunction]) -> None:
        """
        批量添加 reducers。

        Args:
            reducers: 包含功能模組鍵與 reducer 的字典。
        """
        for key, r in reducers.items():
            self.add_reducer(key, r)

    def remove_reducer(self, feature_key: str) -> None:
        """
        移除指定功能模組的 reducer。

        Args:
            feature_key: 要移除的功能模組鍵。
        """
        if feature_key in self._feature_reducers:
            del self._feature_reducers[feature_key]
            del self._state[feature_key]

    def get_reducers(self) -> Dict[str, ReducerFunction]:
        """
        獲取當前所有的 reducers。

        Returns:
            一個包含所有功能模組鍵與 reducer 的字典。
        """
        return self._feature_reducers.copy()

    def reduce(self, state: Optional[Dict[str, Any]] = None, action: Optional[Action[Any]] = None) -> Dict[str, Any]:
        """
        使用所有註冊的 reducers 處理 action 並返回新狀態。

        Args:
            state: 當前的 root state，默認為 None。
            action: 要處理的 action，默認為 None。

        Returns:
            新的 root state。
        """
        if state is None:
            state = self._state  # 如果 state 為 None，使用內部的 _state

        new_state = state.copy()  # 浅拷貝，避免修改原始 state

        for feature_key, reducer in self._feature_reducers.items():
            # 獲取當前功能模組的狀態，若不存在則使用初始狀態
            prev_substate = state.get(feature_key, reducer.initial_state)  # type: ignore
            next_substate = reducer(prev_substate, action)  # 使用 reducer 處理 action

            if next_substate is not prev_substate:
                # 如果狀態有變化，更新到新狀態中
                new_state[feature_key] = next_substate

        self._state = new_state  # 保存最新的 root state
        return new_state