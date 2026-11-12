# Visualization and Reporting

<cite>
**Referenced Files in This Document**   
- [fpl.py](file://premier-league/fpl.py)
- [make_pl_video.py](file://premier-league/make_pl_video.py)
- [main.py](file://DASHBOARD/main.py)
- [elo.py](file://worldcup26/1998/elo.py)
- [fullsim.py](file://worldcup26/Glicko2ratingversion/fullsim.py)
</cite>

## Table of Contents
1. [Introduction](#introduction)
2. [Project Structure](#project-structure)
3. [Core Components](#core-components)
4. [Architecture Overview](#architecture-overview)
5. [Detailed Component Analysis](#detailed-component-analysis)
6. [Dependency Analysis](#dependency-analysis)
7. [Performance Considerations](#performance-considerations)
8. [Troubleshooting Guide](#troubleshooting-guide)
9. [Conclusion](#conclusion)

## Introduction
This document explains the visualization and reporting capabilities across the project, focusing on:
- Chart generation for statistical plots, probability distributions, and comparative analysis
- High-resolution PNG export with customizable styling and formatting
- Animated video generation that shows table evolution over time
- Interactive world map visualization with continent filtering, league marker positioning, and hover interactions
- Report formatting options, template customization, and automated report generation workflows
- Performance considerations for large datasets and rendering efficiency

The system combines static charting, interactive dashboards, animated videos, and PDF-style reports to present Monte Carlo simulation results from multiple sports leagues and tournaments.

## Project Structure
The visualization and reporting features are primarily implemented in three areas:
- Premier League chart generator producing styled 1280x720 PNGs
- Dashboard application providing interactive screens, world map, detail views, PNG export, and MP4 export
- Video pipeline generating progressive simulations as MP4 files
- Report templates using a PDF library for structured documents

```mermaid
graph TB
subgraph "Charts"
FPL["Premier League Charts<br/>fpl.py"]
end
subgraph "Dashboard"
DASH["Interactive Dashboard<br/>DASHBOARD/main.py"]
end
subgraph "Video Pipeline"
PLVID["PL Progress Video<br/>premier-league/make_pl_video.py"]
NFLVID["NFL Frame Renderer<br/>NFL/video.py"]
end
subgraph "Reports"
WC1998["World Cup 1998 Report<br/>worldcup26/1998/elo.py"]
GICKO["Glicko2 Report Builder<br/>worldcup26/Glicko2ratingversion/fullsim.py"]
end
FPL --> |"PNG charts"| OUT1["charts/*.png"]
DASH --> |"PNG export"| OUT2["detail.png"]
DASH --> |"MP4 export"| OUT3["progress.mp4"]
PLVID --> |"MP4 frames"| OUT4["pl_table_*.mp4"]
NFLVID --> |"Frame bytes"| OUT5["video frames"]
WC1998 --> |"PDF pages"| OUT6["report.pdf"]
GICKO --> |"PDF tables"| OUT7["report.pdf"]
```

**Diagram sources**
- [fpl.py:1-804](file://premier-league/fpl.py#L1-L804)
- [main.py:1-1633](file://DASHBOARD/main.py#L1-L1633)
- [make_pl_video.py:1-308](file://premier-league/make_pl_video.py#L1-L308)
- [elo.py:1-200](file://worldcup26/1998/elo.py#L1-L200)
- [fullsim.py:1820-1844](file://worldcup26/Glicko2ratingversion/fullsim.py#L1820-L1844)

**Section sources**
- [fpl.py:1-804](file://premier-league/fpl.py#L1-L804)
- [main.py:1-1633](file://DASHBOARD/main.py#L1-L1633)
- [make_pl_video.py:1-308](file://premier-league/make_pl_video.py#L1-L308)
- [elo.py:1-200](file://worldcup26/1998/elo.py#L1-L200)
- [fullsim.py:1820-1844](file://worldcup26/Glicko2ratingversion/fullsim.py#L1820-L1844)

## Core Components
- Chart Generator (Premier League): Produces 25 infographic-style PNGs covering title probabilities, qualification chances, European performance, Elo ratings, and more. Uses Matplotlib with custom color palettes and fixed canvas dimensions.
- Dashboard Application: Provides multi-screen navigation including progress tracking, home grid, world map, detail view, and video playback. Supports high-resolution PNG export and MP4 export of evolving tables.
- Video Pipeline: Renders per-simulation snapshots into an MP4 with parallel frame rendering and ffmpeg integration. Includes audio looping and configurable duration.
- Report Templates: Uses a PDF library to build structured documents with styled tables, paragraphs, and page layouts.

**Section sources**
- [fpl.py:1-804](file://premier-league/fpl.py#L1-L804)
- [main.py:1-1633](file://DASHBOARD/main.py#L1-L1633)
- [make_pl_video.py:1-308](file://premier-league/make_pl_video.py#L1-L308)
- [elo.py:1-200](file://worldcup26/1998/elo.py#L1-L200)
- [fullsim.py:1820-1844](file://worldcup26/Glicko2ratingversion/fullsim.py#L1820-L1844)

## Architecture Overview
The visualization and reporting architecture integrates several subsystems:
- Simulation modules produce results and snapshots
- Chart generator consumes results to create static PNGs
- Dashboard renders interactive UIs and exports media
- Video pipeline converts snapshots into animated MP4s
- Report builders assemble PDF documents with tables and narratives

```mermaid
sequenceDiagram
participant Sim as "Simulation Module"
participant Charts as "Chart Generator"
participant Dash as "Dashboard App"
participant Vid as "Video Pipeline"
participant Rep as "Report Builder"
Sim->>Sim : run_simulation(n_sims)
Sim-->>Dash : results + snapshots
Sim-->>Vid : snapshots
Dash->>Dash : render_detail_png()
Dash->>Dash : _export_progress_video()
Vid->>Vid : render_frame(snapshot)
Vid->>Vid : ffmpeg encode frames
Rep->>Rep : SimpleDocTemplate + TableStyle
Rep->>Rep : write PDF
```

**Diagram sources**
- [main.py:284-331](file://DASHBOARD/main.py#L284-L331)
- [main.py:1373-1456](file://DASHBOARD/main.py#L1373-L1456)
- [make_pl_video.py:214-308](file://premier-league/make_pl_video.py#L214-L308)
- [elo.py:6-13](file://worldcup26/1998/elo.py#L6-L13)

## Detailed Component Analysis

### Chart Generation System
The chart generator produces 25 distinct visualizations:
- Hero cards with big numbers and stacked bars
- Horizontal bar charts for probabilities and statistics
- Three-stat cards for summary metrics
- Custom color palette and typography for consistent branding

Key capabilities:
- Statistical plots: average points, finish positions, thresholds
- Probability distributions: title race, UCL/UEL/UECL qualification, relegation
- Comparative analysis: association coefficients, Elo ratings, European win chances

Rendering details:
- Fixed 1280x720 canvas at 100 DPI
- Dark green background with cream/yellow/teal accents
- Automatic font sizing for long tables
- Clean PNG output with directory management

```mermaid
flowchart TD
Start(["Start make_all_charts"]) --> LoadData["Load simulation results"]
LoadData --> PrepareStats["Prepare stats: sorted teams, top-n filters"]
PrepareStats --> DrawHero["Draw hero card"]
PrepareStats --> DrawBars["Draw horizontal bars"]
PrepareStats --> DrawThree["Draw three stats"]
DrawHero --> SavePNG["Save PNG"]
DrawBars --> SavePNG
DrawThree --> SavePNG
SavePNG --> NextChart{"More charts?"}
NextChart --> |Yes| PrepareStats
NextChart --> |No| End(["Done"])
```

**Diagram sources**
- [fpl.py:354-760](file://premier-league/fpl.py#L354-L760)
- [fpl.py:142-290](file://premier-league/fpl.py#L142-L290)

**Section sources**
- [fpl.py:1-804](file://premier-league/fpl.py#L1-L804)

### Image Export Functionality
High-resolution PNG export is implemented in two contexts:
- Static charts via Matplotlib savefig
- Dashboard detail views via Qt painter scaling

Features:
- Configurable DPI and canvas size
- Antialiasing enabled for crisp text and graphics
- Background color customization
- Directory creation and file writing with error handling

Export workflow:
- Build widget hierarchy with titles, subtitles, and data tables
- Render to offscreen QPixmap with scale factor
- Convert to PNG format and save to disk

```mermaid
sequenceDiagram
participant User as "User"
participant Detail as "DetailScreen"
participant Render as "_render_detail_png"
participant Painter as "QPainter"
User->>Detail : Click "Save PNG"
Detail->>Render : _render_detail_png(spec, results, path)
Render->>Render : Build container + body
Render->>Painter : Create QPixmap with scale
Painter->>Painter : Render widget to image
Painter-->>Render : PNG bytes
Render->>Render : pix.save(path, "PNG")
Render-->>Detail : Success or exception
Detail-->>User : Show saved message or error
```

**Diagram sources**
- [main.py:1517-1562](file://DASHBOARD/main.py#L1517-L1562)
- [main.py:660-686](file://DASHBOARD/main.py#L660-L686)

**Section sources**
- [main.py:660-686](file://DASHBOARD/main.py#L660-L686)
- [main.py:1517-1562](file://DASHBOARD/main.py#L1517-L1562)

### Animated Video Generation System
Two video systems exist:
- Dashboard MP4 export: Converts Qt-rendered frames to MP4 using OpenCV
- Premier League video pipeline: Parallel frame rendering with ffmpeg

Capabilities:
- Progressive simulation display showing table evolution
- Interpolated snapshots for smooth transitions
- Configurable duration and frame rate
- Audio looping support (PL pipeline)

Rendering pipeline:
- Capture snapshots during simulation runs
- Build video container with frozen team order
- Render frames at target resolution
- Encode with ffmpeg or OpenCV writer

```mermaid
flowchart TD
Snapshots["Simulation Snapshots"] --> BuildContainer["_build_video_container"]
BuildContainer --> FrozenOrder["_frozen_team_order"]
FrozenOrder --> RenderLoop["Frame Rendering Loop"]
RenderLoop --> UpdateTable["_update_video_container"]
UpdateTable --> RenderFrame["Qt Painter -> QPixmap"]
RenderFrame --> Convert["RGB -> BGR conversion"]
Convert --> Writer["OpenCV Writer / ffmpeg stdin"]
Writer --> Output["MP4 File"]
```

**Diagram sources**
- [main.py:1268-1456](file://DASHBOARD/main.py#L1268-L1456)
- [make_pl_video.py:73-141](file://premier-league/make_pl_video.py#L73-L141)
- [make_pl_video.py:248-308](file://premier-league/make_pl_video.py#L248-L308)

**Section sources**
- [main.py:1037-1456](file://DASHBOARD/main.py#L1037-L1456)
- [make_pl_video.py:1-308](file://premier-league/make_pl_video.py#L1-L308)

### Interactive World Map Visualization
The dashboard includes a comprehensive world map with:
- Continent filtering via click interactions
- League marker positioning based on geographic coordinates
- Hover effects highlighting continents and markers
- Side panel listing competitions filtered by continent

Implementation details:
- Custom QPainter-based rendering for continents and markers
- Coordinate transformation from lon/lat to screen space
- Hit detection for markers and continent polygons
- Signal-based communication between map and side panel

```mermaid
classDiagram
class WorldMapWidget {
+results
+league_clicked
+continent_selected
-_hover_key
-_hover_cont
-_selected_cont
-_markers
-_continent_paths
+paintEvent(ev)
+mouseMoveEvent(e)
+mousePressEvent(e)
+set_selected_continent(name)
-_to_screen(lon, lat, rect)
-_build_geometry()
-_hit_marker(pos)
-_hit_continent(pos)
}
class MapSidePanel {
+league_clicked
+show_all
-_continent
+set_continent(name)
}
class MapScreen {
+on_open
+on_back
-map
-panel
-_clear_selection()
}
WorldMapWidget --> MapSidePanel : "signals"
MapScreen --> WorldMapWidget : "contains"
MapScreen --> MapSidePanel : "contains"
```

**Diagram sources**
- [main.py:742-907](file://DASHBOARD/main.py#L742-L907)
- [main.py:913-1004](file://DASHBOARD/main.py#L913-L1004)

**Section sources**
- [main.py:692-907](file://DASHBOARD/main.py#L692-L907)
- [main.py:913-1004](file://DASHBOARD/main.py#L913-L1004)

### Report Formatting Options and Template Customization
Report generation uses a PDF library to create structured documents:
- Page layout configuration with letter-sized pages
- Styled tables with headers, alternating colors, and borders
- Paragraph styles for headings and body text
- Dynamic content insertion for simulation results

Template customization includes:
- Column width configuration for optimal readability
- Font sizing and alignment settings
- Color schemes for headers and backgrounds
- Spacing and padding adjustments

```mermaid
flowchart TD
Start(["Build Report"]) --> SetupDoc["SimpleDocTemplate setup"]
SetupDoc --> AddContent["Add paragraphs and tables"]
AddContent --> StyleTables["Apply TableStyle"]
StyleTables --> InsertData["Insert simulation data"]
InsertData --> GeneratePDF["Generate PDF document"]
GeneratePDF --> End(["Report Complete"])
```

**Diagram sources**
- [elo.py:6-13](file://worldcup26/1998/elo.py#L6-L13)
- [fullsim.py:1820-1844](file://worldcup26/Glicko2ratingversion/fullsim.py#L1820-L1844)

**Section sources**
- [elo.py:1-200](file://worldcup26/1998/elo.py#L1-L200)
- [fullsim.py:1820-1844](file://worldcup26/Glicko2ratingversion/fullsim.py#L1820-L1844)

## Dependency Analysis
The visualization and reporting system has clear dependency relationships:

```mermaid
graph TD
SimModules["Simulation Modules"] --> Results["Results Data"]
Results --> Charts["Chart Generator"]
Results --> Dashboard["Dashboard App"]
Results --> VideoPipeline["Video Pipeline"]
Charts --> Matplotlib["Matplotlib"]
Dashboard --> PyQt5["PyQt5"]
Dashboard --> OpenCV["OpenCV (optional)"]
VideoPipeline --> PIL["PIL/Pillow"]
VideoPipeline --> FFmpeg["FFmpeg (external)"]
Reports --> ReportLab["ReportLab"]
Charts --> PNG["PNG Files"]
Dashboard --> PNG
Dashboard --> MP4["MP4 Files"]
VideoPipeline --> MP4
Reports --> PDF["PDF Files"]
```

**Diagram sources**
- [fpl.py:45-50](file://premier-league/fpl.py#L45-L50)
- [main.py:20-31](file://DASHBOARD/main.py#L20-L31)
- [make_pl_video.py:25-26](file://premier-league/make_pl_video.py#L25-L26)
- [elo.py:6-13](file://worldcup26/1998/elo.py#L6-L13)

**Section sources**
- [fpl.py:45-50](file://premier-league/fpl.py#L45-L50)
- [main.py:20-31](file://DASHBOARD/main.py#L20-L31)
- [make_pl_video.py:25-26](file://premier-league/make_pl_video.py#L25-L26)
- [elo.py:6-13](file://worldcup26/1998/elo.py#L6-L13)

## Performance Considerations
Several optimization techniques are employed throughout the system:

### Chart Generation
- Batch processing of 25 charts with consistent styling
- Efficient data preparation with sorting and filtering
- Memory cleanup after each chart save
- Fixed canvas dimensions for predictable rendering

### Dashboard Rendering
- Offscreen rendering for PNG export to avoid UI updates
- Antialiasing enabled for high-quality output
- Scaled pixel maps for high-resolution images
- Widget reuse and proper cleanup to prevent memory leaks

### Video Generation
- Parallel frame rendering using ProcessPoolExecutor
- Queue-based producer-consumer pattern for frame processing
- Optimized ffmpeg command line with appropriate codecs
- Audio streaming without blocking video encoding

### Large Dataset Handling
- Snapshot interpolation for smooth animations
- Frozen team ordering to prevent row swapping
- Efficient data structures for probability calculations
- Incremental rendering for large tables

**Section sources**
- [fpl.py:103-125](file://premier-league/fpl.py#L103-L125)
- [main.py:673-684](file://DASHBOARD/main.py#L673-L684)
- [make_pl_video.py:280-295](file://premier-league/make_pl_video.py#L280-L295)

## Troubleshooting Guide

### Common Issues and Solutions

#### PNG Export Failures
- **Issue**: Could not write PNG file
- **Cause**: Permission issues or invalid path
- **Solution**: Check file permissions and ensure directory exists

#### Video Export Dependencies
- **Issue**: Missing OpenCV or numpy for MP4 export
- **Cause**: Optional dependencies not installed
- **Solution**: Install opencv-python and numpy packages

#### FFmpeg Integration
- **Issue**: FFmpeg could not open output file
- **Cause**: Missing codec or invalid path
- **Solution**: Install ffmpeg and verify output path permissions

#### Font Loading Problems
- **Issue**: Fonts not found in video rendering
- **Cause**: Platform-specific font paths
- **Solution**: Ensure fonts are available or use fallback fonts

#### Memory Issues with Large Datasets
- **Issue**: High memory usage during rendering
- **Cause**: Too many widgets or large images
- **Solution**: Use batch processing and proper cleanup

**Section sources**
- [main.py:685-686](file://DASHBOARD/main.py#L685-L686)
- [main.py:1375-1380](file://DASHBOARD/main.py#L1375-L1380)
- [main.py:1404-1407](file://DASHBOARD/main.py#L1404-L1407)
- [make_pl_video.py:49-55](file://premier-league/make_pl_video.py#L49-L55)

## Conclusion
The visualization and reporting system provides comprehensive tools for presenting sports simulation results through multiple formats:
- Static charts for detailed statistical analysis
- Interactive dashboards for exploration and presentation
- Animated videos for dynamic storytelling
- Structured reports for documentation and sharing

The system balances performance with quality, offering both real-time interactivity and high-fidelity output suitable for various audiences and use cases. The modular architecture allows for easy extension and customization while maintaining consistency across different visualization types.