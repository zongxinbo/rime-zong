local M = {}

local CONFIG_ROOT = "aux_code_filter"
local DEFAULT_DICTIONARY = "cangjie5"
local DEFAULT_SEPARATORS = ";,"
local DEFAULT_MATCH_STRATEGY = "word_first_last"
local DEFAULT_MAX_CODE_LENGTH = 2
local DEFAULT_PROPERTY_PREFIX = "aux_code_filter"

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
  local match_strategy = config_string(config, CONFIG_ROOT .. "/match_strategy", "")
  if match_strategy == "" then
    match_strategy = config_string(config, CONFIG_ROOT .. "/target", DEFAULT_MATCH_STRATEGY)
  end
  local settings = {
    dictionary = config_string(config, CONFIG_ROOT .. "/dictionary", DEFAULT_DICTIONARY),
    match_strategy = match_strategy,
    max_code_length = config_int(config, CONFIG_ROOT .. "/max_code_length", DEFAULT_MAX_CODE_LENGTH),
    show_prompt = config_bool(config, CONFIG_ROOT .. "/show_prompt", true),
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

local function split_codes(code_string)
  local codes = {}
  for code in (code_string or ""):gmatch("[a-z]+") do
    if not code:match("^[xz]") then
      table.insert(codes, code)
    end
  end
  return codes
end

local function code_matches(aux, code, settings)
  local key = (aux or ""):sub(1, settings.max_code_length)
  if key == "" then
    return true
  end
  if #key == 1 then
    return code:sub(1, 1) == key
  end
  return #code >= 1 and (code:sub(1, 1) .. code:sub(-1)) == key
end

local function first_code_char(reverse, text)
  local char = first_utf8_char(text)
  if char == "" then
    return ""
  end
  for _, code in ipairs(split_codes(reverse:lookup(char))) do
    if code ~= "" then
      return code:sub(1, 1)
    end
  end
  return ""
end

local function word_first_last_matches(aux, text, reverse, settings)
  local key = (aux or ""):sub(1, settings.max_code_length)
  if key == "" then
    return true
  end
  if utf8_len(text) <= 1 then
    for _, code in ipairs(split_codes(reverse:lookup(text))) do
      if code_matches(key, code, settings) then
        return true
      end
    end
    return false
  end

  local first_code = first_code_char(reverse, text)
  if #key == 1 then
    return first_code == key
  end

  local last_code = first_code_char(reverse, last_utf8_char(text))
  return first_code ~= "" and last_code ~= "" and (first_code .. last_code) == key
end

local function sync_prompt(ctx, settings)
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
        for _, code in ipairs(split_codes(reverse:lookup(char))) do
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
