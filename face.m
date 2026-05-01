% =========================================================================
% 论文复现: A visual search advantage for illusory faces in objects (Keys et al., 2021)
% 依赖环境: MATLAB + Psychtoolbox-3
% =========================================================================

function RunIllusoryFaceSearchExp()
    % 1. 基础设置与初始化
    PsychDefaultSetup(2);
    Screen('Preference', 'SkipSyncTests', 1); % 测试阶段可跳过同步测试，正式实验请设为0
    
    % 设置按键 (根据论文，使用左右手按键分别代表不存在和存在)
    KbName('UnifyKeyNames');
    presentKey = KbName('RightArrow'); % 模拟红色按钮 (Right hand)
    absentKey = KbName('LeftArrow');   % 模拟黑色按钮 (Left hand)
    escapeKey = KbName('ESCAPE');

    % 获取屏幕并设置背景为黑色
    screens = Screen('Screens');
    screenNumber = max(screens);
    black = BlackIndex(screenNumber);
    [window, windowRect] = PsychImaging('OpenWindow', screenNumber, black);
    [xCenter, yCenter] = RectCenter(windowRect);
    
    % 时间参数设置 (单位: 秒)
    targetDuration = 1.600;       % 目标呈现 1600 ms
    fixationMin = 0.400;          % 注视点最小 400 ms
    fixationMax = 0.600;          % 注视点最大 600 ms
    maxResponseTime = 15.000;     % 最大超时 15,000 ms
    feedbackDuration = 0.250;     % 反馈呈现 250 ms
    
    % 颜色设置
    gray = [128 128 128];
    green = [0 255 0];            % 正确反馈颜色
    red = [255 0 0];              % 错误反馈颜色

    % 假设的 Trial 循环 (这里以 1 个 Trial 为例演示核心逻辑)
    numTrials = 1; 
    
    for trial = 1:numTrials
        % -----------------------------------------------------------------
        % 阶段 A: 呈现目标图像 (Target) 1600 ms
        % -----------------------------------------------------------------
        % [注: 此处需使用 Screen('MakeTexture') 将你的图片转换为纹理]
        % 这里用一个灰色方块代替目标图片
        targetRect = [0 0 100 100]; 
        centeredTargetRect = CenterRectOnPointd(targetRect, xCenter, yCenter);
        Screen('FillRect', window, gray, centeredTargetRect);
        Screen('Flip', window);
        WaitSecs(targetDuration);
        
        % -----------------------------------------------------------------
        % 阶段 B: 呈现注视点 (Fixation Cross) 400-600 ms 随机
        % -----------------------------------------------------------------
        fixDuration = fixationMin + (fixationMax - fixationMin) * rand();
        DrawFormattedText(window, '+', 'center', 'center', gray);
        Screen('Flip', window);
        WaitSecs(fixDuration);
        
        % -----------------------------------------------------------------
        % 阶段 C: 呈现搜索阵列 (Search Array) 并等待按键
        % -----------------------------------------------------------------
        % 论文中提到的两种布局方式：
        experimentType = 1; % 改为 2 可测试实验二的圆形布局
        
        if experimentType == 1
            % 实验1: 8x8 隐形网格 (Set sizes: 16, 32, 64)
            setSize = 32; % 示例: 32 items
            drawGridArray(window, xCenter, yCenter, setSize);
        else
            % 实验2: 圆形阵列 (Set sizes: 4, 8, 16)
            setSize = 8;  % 示例: 8 items
            drawCircularArray(window, xCenter, yCenter, setSize);
        end
        
        arrayOnsetTime = Screen('Flip', window);
        
        % 等待被试反应
        responseMade = false;
        isCorrect = false;
        targetIsPresent = true; % 假设当前 Trial 目标存在
        
        while GetSecs() - arrayOnsetTime < maxResponseTime
            [keyIsDown, secs, keyCode] = KbCheck;
            if keyIsDown
                if keyCode(escapeKey)
                    sca; return;
                elseif keyCode(presentKey)
                    responseMade = true;
                    isCorrect = targetIsPresent; % 如果目标存在且按了存在，则正确
                    break;
                elseif keyCode(absentKey)
                    responseMade = true;
                    isCorrect = ~targetIsPresent; % 如果目标不存在且按了不存在，则正确
                    break;
                end
            end
        end
        
        % -----------------------------------------------------------------
        % 阶段 D: 呈现反馈 (Feedback) 250 ms
        % -----------------------------------------------------------------
        if responseMade
            if isCorrect
                feedbackColor = green;
            else
                feedbackColor = red;
            end
            DrawFormattedText(window, '+', 'center', 'center', feedbackColor);
        else
            % 超时处理
            DrawFormattedText(window, 'TIMEOUT', 'center', 'center', red);
        end
        Screen('Flip', window);
        WaitSecs(feedbackDuration);
        
        % 准备进入下一个 Trial（确保屏幕清空）
        Screen('Flip', window);
    end
    
    % 实验结束，清理屏幕
    sca;
end

% =========================================================================
% 辅助函数: 绘制实验1的网格布局
% 根据论文：8x8 搜索网格，每个元素约 2x2 视角度，整体阵列约 17x17 视角度
% =========================================================================
function drawGridArray(window, xCenter, yCenter, setSize)
    gridSize = 8;
    itemSize = 80; % 像素大小 (需要根据实际屏幕分辨率和被试距离校准到 2 度视角)
    spacing = 85;  % 包含间隔的间距
    
    % 生成 8x8 的所有可能坐标
    [xGrid, yGrid] = meshgrid(1:gridSize, 1:gridSize);
    xCoords = (xGrid(:) - 4.5) * spacing + xCenter;
    yCoords = (yGrid(:) - 4.5) * spacing + yCenter;
    
    % 随机打乱坐标并选取 setSize 数量的位置
    randIndices = randperm(gridSize * gridSize, setSize);
    selectedX = xCoords(randIndices);
    selectedY = yCoords(randIndices);
    
    % 在这些位置绘制刺激物 (此处以随机颜色的方块代替图片)
    for i = 1:setSize
        rect = CenterRectOnPointd([0 0 itemSize itemSize], selectedX(i), selectedY(i));
        Screen('FillRect', window, [rand*255 rand*255 rand*255], rect);
    end
end

% =========================================================================
% 辅助函数: 绘制实验2的圆形布局
% 根据论文：元素在距离中心等距的圆环上排列
% =========================================================================
function drawCircularArray(window, xCenter, yCenter, setSize)
    radius = 300;  % 距离中心的半径像素
    itemSize = 80; % 像素大小
    
    % 计算均匀分布的极坐标角度
    angles = linspace(0, 2*pi, setSize + 1);
    angles(end) = []; % 移除重复的 2*pi
    
    % 转换为笛卡尔坐标系
    xCoords = xCenter + radius * cos(angles);
    yCoords = yCenter + radius * sin(angles);
    
    % 在这些位置绘制刺激物
    for i = 1:setSize
        rect = CenterRectOnPointd([0 0 itemSize itemSize], xCoords(i), yCoords(i));
        % 如果想插入真实纹理: Screen('DrawTexture', window, textureIndex, [], rect);
        Screen('FillOval', window, [rand*255 rand*255 rand*255], rect);
    end
end