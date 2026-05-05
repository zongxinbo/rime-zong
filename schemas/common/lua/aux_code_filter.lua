local M = {}

local CONFIG_ROOT = "aux_code_filter"
local DEFAULT_DICTIONARY = "cangjie5"
local DEFAULT_SEPARATORS = ";,"
local DEFAULT_MATCH_STRATEGY = "word_first_last"
local DEFAULT_MAX_CODE_LENGTH = 2
local DEFAULT_SHOW_PROMPT = true
local DEFAULT_PROPERTY_PREFIX = "aux_code_filter"
local DEFAULT_IGNORED_CODE_PREFIXES = ""
local DEFAULT_LOW_PRIORITY_CODE_PREFIXES = ""

-- Rime 的 key:repr() 对常见标点返回的是按键名，不一定是字符本身。
-- 这里同时登记两种写法，方便 schema 里只配置实际分隔符字符。
local KEY_NAMES = {
  [";"] = "semicolon",
  [","] = "comma",
  ["."] = "period",
  ["/"] = "slash",
  ["'"] = "apostrophe",
  ["`"] = "grave",
  ["["] = "bracketleft",
  ["]"] = "bracketright",
  ["\\"] = "backslash",
}

local function config_string(config, path, default)
  local ok, value = pcall(function()
    return config:get_string(path)
  end)
  if ok and value and value ~= "" then
    return value
  end
  return default
end

local function config_int(config, path, default)
  local ok, value = pcall(function()
    return config:get_int(path)
  end)
  if ok and type(value) == "number" and value > 0 then
    return value
  end
  local text = config_string(config, path, "")
  return tonumber(text) or default
end

local function config_bool(config, path, default)
  local ok, value = pcall(function()
    return config:get_bool(path)
  end)
  if ok and type(value) == "boolean" then
    return value
  end
  local text = config_string(config, path, "")
  if text == "" then
    return default
  end
  text = text:lower()
  return not (text == "false" or text == "0" or text == "no" or text == "off")
end

local function build_separator_map(separators)
  local map = {}
  for separator in (separators or ""):gmatch(".") do
    map[separator] = separator
    if KEY_NAMES[separator] then
      map[KEY_NAMES[separator]] = separator
    end
  end
  return map
end

local function load_settings(env)
  local config = env.engine.schema.config
  local schema_id = config_string(config, "schema/schema_id", DEFAULT_PROPERTY_PREFIX)
  local settings = {
    dictionary = config_string(config, CONFIG_ROOT .. "/dictionary", DEFAULT_DICTIONARY),
    ignored_code_prefixes = config_string(
      config,
      CONFIG_ROOT .. "/ignored_code_prefixes",
      DEFAULT_IGNORED_CODE_PREFIXES
    ),
    low_priority_code_prefixes = config_string(
      config,
      CONFIG_ROOT .. "/low_priority_code_prefixes",
      DEFAULT_LOW_PRIORITY_CODE_PREFIXES
    ),
    match_strategy = config_string(config, CONFIG_ROOT .. "/match_strategy", DEFAULT_MATCH_STRATEGY),
    max_code_length = config_int(config, CONFIG_ROOT .. "/max_code_length", DEFAULT_MAX_CODE_LENGTH),
    show_prompt = config_bool(config, CONFIG_ROOT .. "/show_prompt", DEFAULT_SHOW_PROMPT),
    property_prefix = config_string(config, CONFIG_ROOT .. "/property_prefix", "aux_code_filter_" .. schema_id),
  }
  settings.separators = build_separator_map(
    config_string(config, CONFIG_ROOT .. "/separators", DEFAULT_SEPARATORS)
  )
  settings.max_code_length = math.max(1, math.min(settings.max_code_length, 2))
  settings.prop_code = settings.property_prefix .. "_code"
  settings.prop_base = settings.property_prefix .. "_base"
  settings.prop_separator = settings.property_prefix .. "_separator"
  return settings
end

local function settings(env)
  if not env.aux_code_filter_settings then
    env.aux_code_filter_settings = load_settings(env)
  end
  return env.aux_code_filter_settings
end

local function get_prop(ctx, key)
  return ctx:get_property(key) or ""
end

local function set_state(ctx, settings, code, base, separator)
  -- 辅码不写入 context.input，避免污染拼音输入串；这里只存在 context property。
  ctx:set_property(settings.prop_code, code or "")
  ctx:set_property(settings.prop_base, base or "")
  ctx:set_property(settings.prop_separator, separator or "")
end

local function clear_state(ctx, settings)
  set_state(ctx, settings, "", "", "")
end

local function active_aux(ctx, settings)
  local code = get_prop(ctx, settings.prop_code)
  local base = get_prop(ctx, settings.prop_base)
  local separator = get_prop(ctx, settings.prop_separator)
  return code, base, separator
end

local function last_utf8_char(text)
  return text:match("([%z\1-\127\194-\244][\128-\191]*)$") or ""
end

local function first_utf8_char(text)
  return text:match("^([%z\1-\127\194-\244][\128-\191]*)") or ""
end

local function target_char(text, settings)
  if settings.match_strategy == "first" then
    return first_utf8_char(text)
  end
  return last_utf8_char(text)
end

local function utf8_len(text)
  local _, count = (text or ""):gsub("[^\128-\191]", "")
  return count
end

local function code_is_ignored(code, settings)
  -- 个别码表会把兼容区或特殊字放在某些前缀下；默认不忽略，交给具体方案配置。
  local prefixes = settings.ignored_code_prefixes or ""
  return prefixes ~= "" and code:match("^[" .. prefixes .. "]") ~= nil
end

local function split_codes(code_string, settings)
  local codes = {}
  for code in (code_string or ""):gmatch("[a-z]+") do
    if not code_is_ignored(code, settings) then
      table.insert(codes, code)
    end
  end
  return codes
end

local function code_is_low_priority(code, settings)
  -- 低优先级码不会被丢弃，只在同一个字有多个编码时排在常规码之后。
  -- 适合处理仓颉里的 x/z 兼容码：有常规码时优先常规码，只有兼容码时仍可匹配。
  local prefixes = settings.low_priority_code_prefixes or ""
  return prefixes ~= "" and code:match("^[" .. prefixes .. "]") ~= nil
end

local function preferred_code(codes, settings)
  for _, code in ipairs(codes) do
    if not code_is_low_priority(code, settings) then
      return code
    end
  end
  return codes[1] or ""
end

local function code_matches(aux, code, settings)
  -- 一码匹配首码；两码匹配首码 + 末码。
  local key = (aux or ""):sub(1, settings.max_code_length)
  if key == "" then
    return true
  end
  if #key == 1 then
    return code:sub(1, 1) == key
  end
  return #code >= 1 and (code:sub(1, 1) .. code:sub(-1)) == key
end

local function lookup_codes(reverse, char, settings)
  if char == "" then
    return {}
  end
  return split_codes(reverse:lookup(char), settings)
end

local function utf8_chars(text)
  return (text or ""):gmatch("[%z\1-\127\194-\244][\128-\191]*")
end

local function first_code_info(reverse, text, settings)
  -- 取第一个能查到编码的字符，而不是机械取字符串首字符。
  -- 这样能兼容包含数字、字母、符号的自动注音词条。
  for char in utf8_chars(text) do
    local codes = lookup_codes(reverse, char, settings)
    if #codes > 0 then
      return char, codes
    end
  end
  return "", {}
end

local function last_code_info(reverse, text, settings)
  local last_char = ""
  local last_codes = {}
  for char in utf8_chars(text) do
    local codes = lookup_codes(reverse, char, settings)
    if #codes > 0 then
      last_char = char
      last_codes = codes
    end
  end
  return last_char, last_codes
end

local function code_bearing_char_count(reverse, text, settings, limit)
  local count = 0
  for char in utf8_chars(text) do
    if #lookup_codes(reverse, char, settings) > 0 then
      count = count + 1
      if limit and count >= limit then
        return count
      end
    end
  end
  return count
end

local function word_first_last_matches(aux, text, reverse, settings)
  -- word_first_last:
  -- 单字按该字首末码过滤；词语按首个可编码字符与末个可编码字符的首码过滤。
  local key = (aux or ""):sub(1, settings.max_code_length)
  if key == "" then
    return true
  end
  if utf8_len(text) <= 1 or code_bearing_char_count(reverse, text, settings, 2) <= 1 then
    local _, codes = first_code_info(reverse, text, settings)
    for _, code in ipairs(codes) do
      if code_matches(key, code, settings) then
        return true
      end
    end
    return false
  end

  local _, first_codes = first_code_info(reverse, text, settings)
  local first_code = preferred_code(first_codes, settings):sub(1, 1)
  if #key == 1 then
    return first_code == key
  end

  local _, last_codes = last_code_info(reverse, text, settings)
  local last_code = preferred_code(last_codes, settings):sub(1, 1)
  return first_code ~= "" and last_code ~= "" and (first_code .. last_code) == key
end

local function sync_prompt(ctx, settings)
  -- prompt 只负责把分隔符和辅码显示在编码区，不参与真实输入。
  if not settings.show_prompt then
    return
  end
  if not ctx then
    return
  end
  local composition = ctx.composition
  if not composition or composition:empty() then
    return
  end
  local aux, base, separator = active_aux(ctx, settings)
  local segment = composition:back()
  if not segment then
    return
  end
  if base ~= "" then
    segment.prompt = (separator ~= "" and separator or ";") .. aux
  else
    segment.prompt = ""
  end
end

local function processor_init(env)
  local s = settings(env)
  local ctx = env.engine.context
  env.update_conn = ctx.update_notifier:connect(function(context)
    local _, base = active_aux(context, s)
    if context.input == "" then
      clear_state(context, s)
      sync_prompt(context, s)
      return
    end
    if base ~= "" and context.input ~= base then
      clear_state(context, s)
      sync_prompt(context, s)
    end
  end)
  env.commit_conn = ctx.commit_notifier:connect(function(context)
    clear_state(context, s)
  end)
  env.delete_conn = ctx.delete_notifier:connect(function(context)
    if context.input == "" then
      clear_state(context, s)
    end
  end)
end

local function processor_fini(env)
  if env.update_conn then
    env.update_conn:disconnect()
  end
  if env.commit_conn then
    env.commit_conn:disconnect()
  end
  if env.delete_conn then
    env.delete_conn:disconnect()
  end
end

local function refresh_menu(ctx, settings)
  -- 辅码状态变化不会自动重算候选，需要主动刷新当前未确认的组合。
  if ctx and ctx:is_composing() then
    ctx:refresh_non_confirmed_composition()
  end
  sync_prompt(ctx, settings)
end

local function processor_func(key, env)
  local s = settings(env)
  local ctx = env.engine.context
  local aux, base, separator = active_aux(ctx, s)
  local repr = key:repr()
  local typed_separator = s.separators[repr]

  if typed_separator and ctx:is_composing() and base == "" then
    set_state(ctx, s, "", ctx.input or "", typed_separator)
    refresh_menu(ctx, s)
    return 1
  end

  if base ~= "" then
    if typed_separator then
      -- 已在辅码状态时再次按分隔符要吞掉，避免触发标点上屏或首选提交。
      refresh_menu(ctx, s)
      return 1
    end

    if repr == "BackSpace" then
      if aux ~= "" then
        set_state(ctx, s, aux:sub(1, -2), base, separator)
      else
        clear_state(ctx, s)
      end
      refresh_menu(ctx, s)
      return 1
    end

    if #repr == 1 and repr:match("^[a-z]$") then
      if #aux < s.max_code_length then
        set_state(ctx, s, aux .. repr, base, separator)
        refresh_menu(ctx, s)
      end
      return 1
    end

    if repr == "Escape" then
      clear_state(ctx, s)
      refresh_menu(ctx, s)
    end
  end

  return 2
end

local function filter_func(input, env)
  local s = settings(env)
  local ctx = env.engine.context
  local aux, base = active_aux(ctx, s)

  if base ~= "" and ctx.input ~= "" and ctx.input ~= base then
    clear_state(ctx, s)
    aux = ""
    sync_prompt(ctx, s)
  end

  if aux == "" then
    for cand in input:iter() do
      yield(cand)
    end
    return
  end

  local reverse = env.reverse or ReverseLookup(s.dictionary)
  env.reverse = reverse

  for cand in input:iter() do
    local matched = false
    if s.match_strategy == "word_first_last" then
      matched = word_first_last_matches(aux, cand.text, reverse, s)
    else
      local char = target_char(cand.text, s)
      if char ~= "" then
      for _, code in ipairs(split_codes(reverse:lookup(char), s)) do
          if code_matches(aux, code, s) then
            matched = true
            break
          end
        end
      end
    end
    if matched then
      yield(cand)
    end
  end
end

M.processor = {
  init = processor_init,
  func = processor_func,
  fini = processor_fini,
}

M.filter = {
  func = filter_func,
}

return M
