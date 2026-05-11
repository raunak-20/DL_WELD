"""
Weld Defect Scan Report Generator - PDF Template
=================================================
Generates professional PDF reports for AI-based weld defect detection scans.
Uses ReportLab to create multi-page reports with:
  - Cover page with scan metadata
  - Scan summary with defect overview
  - Detailed defect findings with annotated images

Usage:
    from weld_report_template import generate_report
    generate_report(scan_data, output_path="scan_report.pdf")
"""

import os
import io
import math
from datetime import datetime
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm, cm, inch
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT, TA_JUSTIFY
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, Image, HRFlowable, KeepTogether, ListFlowable, ListItem
)
from reportlab.pdfgen import canvas
from reportlab.graphics.shapes import Drawing, Rect, String, Line, Circle
from reportlab.graphics.charts.barcharts import VerticalBarChart
from reportlab.graphics.charts.piecharts import Pie
from reportlab.graphics import renderPDF
from PIL import Image as PILImage
from reportlab.platypus import Image

# ─────────────────────────────────────────────────────────────────────────────
# COLOR PALETTE
# ─────────────────────────────────────────────────────────────────────────────
NAVY       = colors.HexColor("#1B2A4A")
DARK_BLUE  = colors.HexColor("#2C3E6B")
ACCENT     = colors.HexColor("#E8792F")  # Orange accent
LIGHT_GRAY = colors.HexColor("#F4F5F7")
MID_GRAY   = colors.HexColor("#D0D3D9")
DARK_GRAY  = colors.HexColor("#4A4A4A")
WHITE      = colors.white
BLACK      = colors.black
RED_CRIT   = colors.HexColor("#C0392B")
AMBER_HIGH = colors.HexColor("#E67E22")
YELLOW_MED = colors.HexColor("#F1C40F")
GREEN_LOW  = colors.HexColor("#27AE60")
GREEN_PASS = colors.HexColor("#2ECC71")

# ─────────────────────────────────────────────────────────────────────────────
# DEFECT KNOWLEDGE BASE (from research paper + RPN data)
# ─────────────────────────────────────────────────────────────────────────────
DEFECT_DATABASE = {
    "Crack": {
        "rpn": 400,
        "severity": "CRITICAL",
        "color": RED_CRIT,
        "surface_visible": True,
        "description": "Linear discontinuity caused by rapid cooling, thermal shrinkage, or base material incompatibility. Can propagate under cyclic loading and cause catastrophic failure.",
        "primary_causes": "Rapid cooling, high residual stress, hydrogen embrittlement, incompatible filler material, improper preheat.",
        "industry_criticality": {
            "Aerospace": ("CRITICAL", "Even micro-cracks can grow under fatigue loading, leading to catastrophic structural failure. Zero tolerance in flight-critical joints."),
            "Oil & Gas": ("CRITICAL", "Cracks in pipelines or pressure vessels can propagate under cyclic pressure, leading to leaks, explosions, or environmental disasters."),
            "Automotive": ("HIGH", "Critical in chassis and suspension welds that bear dynamic loads. Acceptable in non-structural cosmetic welds only."),
            "Construction": ("HIGH", "Reduces fatigue resistance in bridges and steel structures. Standards like AWS D1.1 generally reject cracks."),
            "Shipbuilding": ("CRITICAL", "Cracks in hull welds below waterline can lead to flooding. Corrosion accelerates crack growth in marine environments."),
        },
        "standards_ref": "Rejected per ISO 5817 Level B; AWS D1.1 rejects all cracks; ASME BPVC Section VIII - no cracks permitted.",
        "recommended_action": "Immediate repair required. Grind out defective area and re-weld. Perform supplementary NDT (UT/RT) to verify full removal before re-welding."
    },
    "Porosity": {
        "rpn": 210,
        "severity": "MEDIUM",
        "color": YELLOW_MED,
        "surface_visible": True,
        "description": "Gas pockets trapped within or on the surface of the weld metal. Appears as spherical or elongated voids caused by gas entrapment during solidification.",
        "primary_causes": "Gas entrapment, contamination (oil, moisture, rust), improper shielding gas flow, excessive travel speed, wet electrodes.",
        "industry_criticality": {
            "Aerospace": ("HIGH", "Even small pores reduce fatigue life significantly. Cluster porosity is generally unacceptable in aerospace applications."),
            "Oil & Gas": ("MEDIUM", "Isolated porosity within size limits may be acceptable per API 1104. Cluster porosity near weld root is high-risk."),
            "Automotive": ("MEDIUM", "Acceptable within limits for non-structural welds. Critical in suspension and safety-related joints."),
            "Construction": ("LOW-MEDIUM", "Small isolated pores may be acceptable under ISO 5817 Level C/D. Clustered porosity requires repair."),
            "Shipbuilding": ("MEDIUM", "Surface porosity can trap moisture and accelerate corrosion. Internal porosity reduces joint strength."),
        },
        "standards_ref": "ISO 5817 Level B: max 3% area; API 1104: max individual pore diameter limits apply; AWS D1.1: size and distribution limits.",
        "recommended_action": "Evaluate pore size and distribution. If within acceptance criteria, document and monitor. If exceeding limits, grind and re-weld affected area. Verify shielding gas setup."
    },
    "Lack of Fusion": {
        "rpn": 420,
        "severity": "CRITICAL",
        "color": RED_CRIT,
        "surface_visible": False,
        "description": "Incomplete melting together of the weld metal and base metal or between weld passes. Creates a planar discontinuity that acts as a stress concentrator.",
        "primary_causes": "Insufficient heat input, improper electrode angle, excessive travel speed, poor joint preparation, oxide contamination on groove faces.",
        "industry_criticality": {
            "Aerospace": ("CRITICAL", "Planar defect that drastically reduces fatigue life. Unacceptable in any flight-critical structure."),
            "Oil & Gas": ("CRITICAL", "Acts as stress concentration point in pressurized systems. Can lead to rapid crack propagation under cyclic loading."),
            "Automotive": ("HIGH", "Critical in load-bearing joints. Significantly reduces tensile and fatigue strength of the welded connection."),
            "Construction": ("HIGH", "Reduces effective throat thickness and load-carrying capacity. Rejected under AWS D1.1 for all structural welds."),
            "Shipbuilding": ("CRITICAL", "Compromises watertight integrity. Particularly dangerous in welds below the waterline."),
        },
        "standards_ref": "Rejected in ISO 5817 Level B; AWS D1.1 rejects lack of fusion; ASME BPVC - not permitted in any pressure boundary weld.",
        "recommended_action": "Must be completely removed by grinding/gouging and re-welded. Ultrasonic or radiographic testing recommended to confirm complete removal. Review welding parameters."
    },
    "Lack of Penetration": {
        "rpn": 350,
        "severity": "HIGH",
        "color": AMBER_HIGH,
        "surface_visible": False,
        "description": "Failure of the weld metal to fully extend through the joint thickness. The root of the joint is not completely fused, leaving an unfilled gap.",
        "primary_causes": "Insufficient welding current, excessive root face, inadequate root gap, improper electrode positioning, excessive travel speed.",
        "industry_criticality": {
            "Aerospace": ("CRITICAL", "Reduces effective joint strength below design requirements. Unacceptable in any structural aerospace weld."),
            "Oil & Gas": ("CRITICAL", "In pipelines, lack of penetration at the root creates a notch from which fatigue cracks can initiate under internal pressure."),
            "Automotive": ("HIGH", "Reduces joint strength. Critical in safety-relevant components such as frame and chassis welds."),
            "Construction": ("HIGH", "Particularly dangerous in full-penetration joints required for moment connections in steel structures."),
            "Shipbuilding": ("HIGH", "Reduces weld strength and can compromise hull integrity. Particularly critical in below-waterline welds."),
        },
        "standards_ref": "ISO 5817 Level B: limited acceptance; API 1104: specific limits based on pipe wall thickness; AWS D1.1: generally rejected for CJP welds.",
        "recommended_action": "Back-gouge and re-weld from the root side if accessible. If single-sided access only, complete removal and re-welding required. Adjust current and root gap for subsequent welds."
    },
    "Undercut": {
        "rpn": 188,
        "severity": "MEDIUM",
        "color": YELLOW_MED,
        "surface_visible": True,
        "description": "A groove melted into the base metal adjacent to the weld toe or root, creating a sharp stress concentration that reduces the effective cross-section.",
        "primary_causes": "Excessive heat input, high travel speed, improper electrode angle, excessive arc length, incorrect weaving technique.",
        "industry_criticality": {
            "Aerospace": ("HIGH", "Sharp notch effect significantly reduces fatigue life. Generally unacceptable except within very tight tolerances."),
            "Oil & Gas": ("MEDIUM", "Acceptable within depth limits per API 1104. Deeper undercuts are stress risers under cyclic pressure loading."),
            "Automotive": ("MEDIUM", "Acceptable in non-structural welds. Must be within limits for chassis and safety-critical components."),
            "Construction": ("MEDIUM", "AWS D1.1 allows limited undercut depth (typically <1mm) depending on loading conditions and member type."),
            "Shipbuilding": ("MEDIUM", "Surface undercut can trap moisture and accelerate corrosion. Limits apply based on classification society rules."),
        },
        "standards_ref": "ISO 5817 Level B: max 0.5mm depth; AWS D1.1: max 1/32 inch for statically loaded, 0.01 inch for cyclically loaded structures.",
        "recommended_action": "If within acceptance limits, document and accept. If exceeding limits, weld repair by depositing additional weld metal in the undercut groove. Adjust welding parameters."
    },
    "Spatter": {
        "rpn": 80,
        "severity": "LOW",
        "color": GREEN_LOW,
        "surface_visible": True,
        "description": "Droplets of molten metal expelled during welding that adhere to the base metal surface adjacent to the weld. Primarily a cosmetic defect.",
        "primary_causes": "Incorrect voltage/current settings, unstable arc, improper shielding gas, contaminated base material, excessive wire feed speed.",
        "industry_criticality": {
            "Aerospace": ("LOW-MEDIUM", "Must be removed as it can mask other defects and interfere with NDT. Can cause stress concentration if not removed."),
            "Oil & Gas": ("LOW", "Generally acceptable if removed. Does not significantly affect structural integrity of the joint."),
            "Automotive": ("LOW", "Cosmetic concern in visible areas. Must be removed before painting or coating for corrosion protection."),
            "Construction": ("LOW", "Acceptable in most applications. Should be removed if it interferes with fit-up of subsequent members."),
            "Shipbuilding": ("LOW-MEDIUM", "Must be removed in corrosion-prone areas as spatter can trap moisture and initiate localized corrosion."),
        },
        "standards_ref": "Generally not covered by acceptance criteria but should be removed per good workmanship standards.",
        "recommended_action": "Remove spatter mechanically (grinding, chipping). Adjust welding parameters to minimize occurrence. Check wire feed and shielding gas settings."
    },
    "Burn Through": {
        "rpn": 300,
        "severity": "HIGH",
        "color": AMBER_HIGH,
        "surface_visible": True,
        "description": "Excessive penetration resulting in the weld metal melting completely through the base material, leaving a hole or thin spot at the root.",
        "primary_causes": "Excessive heat input, too slow travel speed, excessive root gap, thin base material, improper joint preparation.",
        "industry_criticality": {
            "Aerospace": ("CRITICAL", "Creates a through-thickness defect that completely compromises joint integrity. Requires complete repair."),
            "Oil & Gas": ("CRITICAL", "In pipeline welding, burn-through creates a potential leak path. Unacceptable in pressure-containing welds."),
            "Automotive": ("HIGH", "Weakens the joint and creates potential corrosion initiation site. Must be repaired in structural applications."),
            "Construction": ("HIGH", "Reduces effective throat and creates stress concentration. Requires repair in structural welds."),
            "Shipbuilding": ("CRITICAL", "Through-thickness defect compromises watertight integrity. Must be repaired before service."),
        },
        "standards_ref": "Generally rejected across all major standards. ISO 5817, AWS D1.1, and ASME BPVC do not permit burn-through.",
        "recommended_action": "Grind out affected area completely and re-weld. Reduce heat input and travel speed adjustments for subsequent passes. Consider backing bar or purge gas setup."
    },
    "Overlap": {
        "rpn": 150,
        "severity": "MEDIUM",
        "color": YELLOW_MED,
        "surface_visible": True,
        "description": "Excess weld metal that flows over the weld toe onto the base metal surface without fusing to it. Creates a mechanical notch and potential crack initiation site.",
        "primary_causes": "Excessive weld metal deposition, too slow travel speed, improper electrode angle, incorrect welding position technique.",
        "industry_criticality": {
            "Aerospace": ("HIGH", "Creates a notch effect that reduces fatigue life. Requires removal and blending."),
            "Oil & Gas": ("MEDIUM", "Acceptable within limits if properly blended. Can mask lack of fusion at the weld toe."),
            "Automotive": ("MEDIUM", "Primarily cosmetic in non-structural welds. Must be removed in fatigue-loaded joints."),
            "Construction": ("MEDIUM", "Can reduce fatigue performance. AWS D1.1 considers overlap as a rejectable discontinuity."),
            "Shipbuilding": ("MEDIUM", "Can trap moisture and accelerate corrosion. Should be removed and blended in corrosion-prone areas."),
        },
        "standards_ref": "ISO 5817 Level B: overlap not permitted; AWS D1.1: classified as a rejectable discontinuity.",
        "recommended_action": "Grind to blend overlap with base metal surface. Ensure proper fusion at the toe. Adjust travel speed and electrode angle."
    },
    "Slag Inclusion": {
        "rpn": 288,
        "severity": "HIGH",
        "color": AMBER_HIGH,
        "surface_visible": False,
        "description": "Non-metallic solid material entrapped in the weld metal or between the weld and base metal. Reduces the effective cross-sectional area and creates stress concentrations.",
        "primary_causes": "Inadequate slag removal between passes, improper welding technique, insufficient heat input, using damaged or wrong electrodes.",
        "industry_criticality": {
            "Aerospace": ("CRITICAL", "Any volumetric inclusion reduces fatigue life and is generally unacceptable in flight-critical structures."),
            "Oil & Gas": ("HIGH", "Reduces effective wall thickness in pressure-containing welds. Limits defined per API 1104 and ASME BPVC."),
            "Automotive": ("MEDIUM", "Acceptable within limits for non-critical welds. Must meet requirements for structural joints."),
            "Construction": ("MEDIUM", "AWS D1.1 defines limits based on inclusion length and thickness. Scattered inclusions may be acceptable."),
            "Shipbuilding": ("HIGH", "Reduces joint strength and can serve as corrosion initiation sites in marine environments."),
        },
        "standards_ref": "ISO 5817 Level B: limited by length and area; API 1104: specific limits based on indication length; ASME BPVC: evaluated per acceptance criteria.",
        "recommended_action": "Remove by grinding/gouging to sound metal and re-weld. Ensure thorough inter-pass slag cleaning. Verify electrode condition and welding technique."
    },
    "Mechanical Mark": {
        "rpn": 60,
        "severity": "LOW",
        "color": GREEN_LOW,
        "surface_visible": True,
        "description": "Surface damage caused by tools, grinding, handling, or accidental contact. Not a welding process defect but can affect surface integrity and mask other defects.",
        "primary_causes": "Improper handling, grinding marks, tool impact, arc strikes from stray arcs, clamp marks.",
        "industry_criticality": {
            "Aerospace": ("MEDIUM", "Must be evaluated for depth and stress concentration effect. Deep marks may require blending or repair."),
            "Oil & Gas": ("LOW", "Generally acceptable if shallow. Deep marks that reduce wall thickness below minimum must be evaluated."),
            "Automotive": ("LOW", "Primarily cosmetic. Only significant if it affects coating adhesion or reduces section thickness."),
            "Construction": ("LOW", "Acceptable in most applications. Arc strikes should be ground smooth per AWS D1.1."),
            "Shipbuilding": ("LOW", "Should be blended smooth to prevent moisture trapping and corrosion initiation."),
        },
        "standards_ref": "Arc strikes are addressed in AWS D1.1 and ISO 5817. Depth limits may apply per project specifications.",
        "recommended_action": "Blend smooth by grinding. If depth exceeds allowable limits, evaluate per engineering requirements. Document location and depth."
    },
    "Underfill": {
        "rpn": 170,
        "severity": "MEDIUM",
        "color": YELLOW_MED,
        "surface_visible": True,
        "description": "A depression on the weld face where the weld metal is insufficient to bring the surface to the level of the base metal. Reduces effective throat thickness.",
        "primary_causes": "Insufficient weld metal deposition, excessive travel speed, improper electrode manipulation, inadequate number of weld passes.",
        "industry_criticality": {
            "Aerospace": ("HIGH", "Reduces effective throat thickness below design requirements. Must meet minimum reinforcement requirements."),
            "Oil & Gas": ("MEDIUM", "Reduces effective wall thickness. Must meet minimum fill requirements per API 1104 and project specifications."),
            "Automotive": ("MEDIUM", "Critical in structural welds where minimum throat thickness is specified for load-bearing capacity."),
            "Construction": ("MEDIUM", "AWS D1.1 specifies minimum acceptable reinforcement levels. Underfill may require additional weld passes."),
            "Shipbuilding": ("MEDIUM", "Reduces joint strength. Classification societies specify minimum weld reinforcement requirements."),
        },
        "standards_ref": "ISO 5817 Level B: limited by depth; AWS D1.1: flush to 1/8 inch reinforcement required; API 1104: minimum fill requirements.",
        "recommended_action": "Deposit additional weld metal to bring surface to required level. Clean surface before adding fill pass. Verify final dimensions meet specification."
    },
    "Arc Strike": {
        "rpn": 120,
        "severity": "LOW-MEDIUM",
        "color": YELLOW_MED,
        "surface_visible": True,
        "description": "Localized damage to the base metal surface caused by inadvertent arcing outside the weld zone. Creates a small heat-affected zone and potential hardness increase.",
        "primary_causes": "Accidental electrode contact with base metal outside weld zone, improper grounding, careless handling of electrode holder.",
        "industry_criticality": {
            "Aerospace": ("HIGH", "Creates localized hard zone that can initiate fatigue cracks. Must be ground smooth and inspected."),
            "Oil & Gas": ("MEDIUM", "Per API 1104, arc strikes must be ground smooth. In sour service, arc strikes are particularly dangerous."),
            "Automotive": ("LOW", "Generally acceptable if ground smooth. Minimal impact on structural performance."),
            "Construction": ("LOW-MEDIUM", "AWS D1.1 requires arc strikes to be ground to smooth contour. Must be inspected for cracks."),
            "Shipbuilding": ("MEDIUM", "Must be ground smooth. Can initiate corrosion in marine environments if not properly treated."),
        },
        "standards_ref": "AWS D1.1: must be ground smooth; API 1104: requires removal; ASME BPVC: must be evaluated.",
        "recommended_action": "Grind smooth and inspect visually and with PT/MT for any cracking. Document location. Implement procedural controls to prevent recurrence."
    },
    "Tack Weld": {
        "rpn": 100,
        "severity": "LOW",
        "color": GREEN_LOW,
        "surface_visible": True,
        "description": "Small temporary welds used to hold parts in alignment during welding. If not properly incorporated into the final weld, they can become discontinuities.",
        "primary_causes": "Not properly incorporated into final weld, insufficient size, cracked tack welds left in place, improper technique.",
        "industry_criticality": {
            "Aerospace": ("MEDIUM", "Must be fully incorporated or removed. Cracked tack welds are unacceptable."),
            "Oil & Gas": ("LOW-MEDIUM", "Should be incorporated into final weld or removed. Quality must match production weld requirements."),
            "Automotive": ("LOW", "Generally incorporated into final weld during production. Stand-alone tack welds should meet minimum quality."),
            "Construction": ("LOW", "Should be of adequate size and quality. AWS D1.1 specifies minimum tack weld requirements."),
            "Shipbuilding": ("LOW", "Must be properly made and incorporated. Cracked tack welds must be removed before final welding."),
        },
        "standards_ref": "AWS D1.1: tack welds must meet specific quality requirements; ISO standards: should be removed or incorporated.",
        "recommended_action": "Ensure tack welds are fully incorporated into the final weld. Remove any tack welds that show cracks. Verify proper fusion at tack weld locations."
    },
    "Excess Penetration": {
        "rpn": 130,
        "severity": "LOW-MEDIUM",
        "color": YELLOW_MED,
        "surface_visible": True,
        "description": "Excessive root reinforcement where weld metal protrudes beyond the root side of the joint more than the specified limit.",
        "primary_causes": "Excessive heat input, too slow travel speed, excessive root gap, improper backing or purge setup.",
        "industry_criticality": {
            "Aerospace": ("MEDIUM", "Must be within specified limits. Excessive reinforcement can cause turbulence in fluid-carrying systems."),
            "Oil & Gas": ("MEDIUM", "In pipelines, excessive internal reinforcement can restrict flow and cause turbulence. Limits per API 1104."),
            "Automotive": ("LOW", "Generally acceptable unless it interferes with fit-up or function of adjacent components."),
            "Construction": ("LOW", "Acceptable within limits. Excessive reinforcement may be ground if it interferes with connections."),
            "Shipbuilding": ("LOW-MEDIUM", "Excessive penetration inside pipe systems can cause flow restrictions and corrosion."),
        },
        "standards_ref": "ISO 5817 Level B: max 1mm + 0.6b; API 1104: max internal reinforcement limits; AWS D1.1: max 1/8 inch.",
        "recommended_action": "If within acceptance limits, document and accept. If exceeding limits, grind internal reinforcement to specified profile where accessible."
    },
    "Suck Back": {
        "rpn": 200,
        "severity": "MEDIUM",
        "color": YELLOW_MED,
        "surface_visible": True,
        "description": "A concavity at the root of the weld caused by shrinkage of the weld pool during solidification. Results in a depression below the original root surface.",
        "primary_causes": "Excessive purge gas pressure, excessive heat input at root, improper root gap or root face dimensions, gravitational effects in certain positions.",
        "industry_criticality": {
            "Aerospace": ("HIGH", "Reduces effective throat thickness at root. Creates stress concentration at internal surface."),
            "Oil & Gas": ("MEDIUM", "Reduces root reinforcement and effective thickness. Must meet internal profile requirements per API 1104."),
            "Automotive": ("LOW-MEDIUM", "Relevant mainly for tubular or pipe joints where root profile is specified."),
            "Construction": ("MEDIUM", "Reduces effective throat in CJP joints. May require additional root passes or repair."),
            "Shipbuilding": ("MEDIUM", "Creates potential stress concentration and corrosion initiation site at internal surface."),
        },
        "standards_ref": "ISO 5817: evaluated as root concavity; API 1104: must meet internal profile requirements; AWS D1.1: limited by depth.",
        "recommended_action": "If root is accessible, deposit additional root pass to fill concavity. Adjust purge pressure and heat input parameters. Consider root backing techniques."
    },
}

# ─────────────────────────────────────────────────────────────────────────────
# SEVERITY HELPERS
# ─────────────────────────────────────────────────────────────────────────────
def severity_color(sev):
    mapping = {"CRITICAL": RED_CRIT, "HIGH": AMBER_HIGH, "MEDIUM": YELLOW_MED,
               "LOW-MEDIUM": YELLOW_MED, "LOW": GREEN_LOW}
    return mapping.get(sev, MID_GRAY)

def severity_rank(sev):
    mapping = {"CRITICAL": 4, "HIGH": 3, "MEDIUM": 2, "LOW-MEDIUM": 1, "LOW": 0}
    return mapping.get(sev, -1)

# ─────────────────────────────────────────────────────────────────────────────
# PAGE TEMPLATES (header/footer)
# ─────────────────────────────────────────────────────────────────────────────
class ReportPageTemplate:
    def __init__(self, scan_data):
        self.scan_data = scan_data

    def header_footer(self, canvas_obj, doc):
        canvas_obj.saveState()
        w, h = A4

        # Header bar
        canvas_obj.setFillColor(NAVY)
        canvas_obj.rect(0, h - 28*mm, w, 28*mm, fill=1, stroke=0)

        logo_path = "static/DSES-Logo.png"

        if os.path.exists(logo_path):
            canvas_obj.drawImage(
                logo_path,
                x=w - 35*mm,   # position (right side)
                y=h - 22.5*mm,
                width=37.5*mm,
                height=18*mm,
                preserveAspectRatio=True,
                # mask='auto'
            )

        # Orange accent line
        canvas_obj.setFillColor(ACCENT)
        canvas_obj.rect(0, h - 29*mm, w, 1*mm, fill=1, stroke=0)

        # Header text
        canvas_obj.setFillColor(WHITE)
        canvas_obj.setFont("Helvetica-Bold", 11)
        canvas_obj.drawString(15*mm, h - 12*mm, "WELD DEFECT INSPECTION REPORT")
        canvas_obj.setFont("Helvetica", 8)
        canvas_obj.drawString(15*mm, h - 19*mm, f"Sample ID: {self.scan_data.get('sample_id', 'N/A')}  |  Scan #{self.scan_data.get('scan_number', 'N/A')}")

        # Footer
        canvas_obj.setFillColor(NAVY)
        canvas_obj.rect(0, 0, w, 12*mm, fill=1, stroke=0)
        canvas_obj.setFillColor(ACCENT)
        canvas_obj.rect(0, 12*mm, w, 0.5*mm, fill=1, stroke=0)

        canvas_obj.setFillColor(WHITE)
        canvas_obj.setFont("Helvetica", 7)
        canvas_obj.drawString(15*mm, 4.5*mm, f"Report ID: {self.scan_data.get('report_id', 'RPT-000001')}  |  CONFIDENTIAL")
        canvas_obj.drawRightString(w - 15*mm, 4.5*mm, f"Page {doc.page}")

        canvas_obj.restoreState()

# ─────────────────────────────────────────────────────────────────────────────
# COVER PAGE
# ─────────────────────────────────────────────────────────────────────────────
def build_cover_page(scan_data):
    elements = []
    w, _ = A4

    elements.append(Spacer(1, 45*mm))

    # Title block
    title_style = ParagraphStyle('CoverTitle', fontName='Helvetica-Bold', fontSize=28,
                                  textColor=NAVY, alignment=TA_CENTER, spaceAfter=5*mm)
    elements.append(Paragraph("WELD DEFECT", title_style))
    elements.append(Paragraph("INSPECTION REPORT", title_style))

    elements.append(Spacer(1, 3*mm))
    elements.append(HRFlowable(width="60%", thickness=2, color=ACCENT, spaceAfter=8*mm, hAlign='CENTER'))

    subtitle_style = ParagraphStyle('CoverSub', fontName='Helvetica', fontSize=13,
                                     textColor=DARK_GRAY, alignment=TA_CENTER, spaceAfter=2*mm)
    elements.append(Paragraph("AI-Powered Visual Inspection System", subtitle_style))
    # elements.append(Paragraph(f"YOLOv8 Detection", subtitle_style))

    elements.append(Spacer(1, 20*mm))

    # Metadata table
    meta_style = ParagraphStyle('Meta', fontName='Helvetica', fontSize=10, textColor=DARK_GRAY)
    meta_bold = ParagraphStyle('MetaBold', fontName='Helvetica-Bold', fontSize=10, textColor=NAVY)

    meta_rows = [
        [Paragraph("Report ID", meta_bold), Paragraph(scan_data.get('report_id', 'RPT-000001'), meta_style)],
        [Paragraph("Sample ID", meta_bold), Paragraph(scan_data.get('sample_id', 'SAMPLE-001'), meta_style)],
        [Paragraph("Scan Number", meta_bold), Paragraph(f"#{scan_data.get('scan_number', 1)}", meta_style)],
        [Paragraph("Scan Date & Time", meta_bold), Paragraph(scan_data.get('scan_date', datetime.now().strftime('%d %b %Y, %H:%M')), meta_style)],
        [Paragraph("Operator", meta_bold), Paragraph(scan_data.get('operator_name', 'N/A'), meta_style)],
        [Paragraph("Location / Site", meta_bold), Paragraph(scan_data.get('location', 'N/A'), meta_style)],
        [Paragraph("Specimen Type", meta_bold), Paragraph(scan_data.get('specimen_type', 'Plate / Pipe'), meta_style)],
        [Paragraph("Joint Configuration", meta_bold), Paragraph(scan_data.get('joint_config', 'Single V Butt Joint'), meta_style)],
        [Paragraph("Material", meta_bold), Paragraph(scan_data.get('material', 'Carbon Steel'), meta_style)],
        [Paragraph("Specimen Size", meta_bold), Paragraph(scan_data.get('specimen_size', 'N/A'), meta_style)],
        [Paragraph("Welding Process", meta_bold), Paragraph(scan_data.get('welding_process', 'SMAW'), meta_style)],
        [Paragraph("Industry / Application", meta_bold), Paragraph(scan_data.get('industry', 'General'), meta_style)],
        [Paragraph("Detection Device", meta_bold), Paragraph(scan_data.get('device', 'Handheld Camera Unit'), meta_style)],
    ]

    meta_table = Table(meta_rows, colWidths=[55*mm, 90*mm])
    meta_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), LIGHT_GRAY),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 0.5, MID_GRAY),
        ('ROWBACKGROUNDS', (0, 0), (-1, -1), [WHITE, LIGHT_GRAY]),
    ]))
    elements.append(meta_table)

    elements.append(Spacer(1, 15*mm))

    elements.append(PageBreak())
    return elements

# ─────────────────────────────────────────────────────────────────────────────
# SECTION: SCAN SUMMARY
# ─────────────────────────────────────────────────────────────────────────────
def build_scan_summary(scan_data, defects_found):
    elements = []

    elements.append(Spacer(1, 18*mm))
    elements.append(section_heading("1. SCAN SUMMARY"))

    body = ParagraphStyle('Body', fontName='Helvetica', fontSize=9.5, textColor=DARK_GRAY,
                           leading=14, spaceAfter=3*mm, alignment=TA_JUSTIFY)
    bold_body = ParagraphStyle('BoldBody', fontName='Helvetica-Bold', fontSize=9.5,
                                textColor=NAVY, spaceAfter=2*mm)

    total_defects = sum(d['count'] for d in defects_found)
    defect_types = len(defects_found)
    highest_sev = "NONE"
    if defects_found:
        sorted_d = sorted(defects_found, key=lambda x: severity_rank(
            DEFECT_DATABASE.get(x['type'], {}).get('severity', 'LOW')), reverse=True)
        highest_sev = DEFECT_DATABASE.get(sorted_d[0]['type'], {}).get('severity', 'UNKNOWN')

    summary_text = (
        f"The AI-powered visual inspection of sample <b>{scan_data.get('sample_id', 'N/A')}</b> "
        f"(Scan #{scan_data.get('scan_number', 'N/A')}) was performed on "
        f"<b>{scan_data.get('scan_date', 'N/A')}</b> using the AI model "
        f"(version {scan_data.get('model_version', 'N/A')}). "
        f"The scan covered the <b>{scan_data.get('scan_side', 'CAP')}</b> side of the weld on a "
        f"<b>{scan_data.get('specimen_type', 'plate')}</b> specimen."
    )
    elements.append(Paragraph(summary_text, body))

    # Quick stats boxes
    stat_style = ParagraphStyle('Stat', fontName='Helvetica-Bold', fontSize=20,
                                 textColor=NAVY, alignment=TA_CENTER)
    stat_label = ParagraphStyle('StatLabel', fontName='Helvetica', fontSize=8,
                                 textColor=DARK_GRAY, alignment=TA_CENTER)

    stats = [
        [Paragraph(str(total_defects), stat_style),
         Paragraph(str(defect_types), stat_style),
         Paragraph(highest_sev, ParagraphStyle('SevStat', fontName='Helvetica-Bold', fontSize=14,
                                                 textColor=severity_color(highest_sev), alignment=TA_CENTER)),
         Paragraph(f"{scan_data.get('confidence_avg', 'N/A')}%", stat_style)],
        [Paragraph("Total Defects", stat_label),
         Paragraph("Defect Types", stat_label),
         Paragraph("Highest Severity", stat_label)],
    ]
    stat_table = Table(stats, colWidths=[42*mm]*4, rowHeights=[16*mm, 8*mm])
    stat_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), LIGHT_GRAY),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BOX', (0, 0), (0, -1), 0.5, MID_GRAY),
        ('BOX', (1, 0), (1, -1), 0.5, MID_GRAY),
        ('BOX', (2, 0), (2, -1), 0.5, MID_GRAY),
        ('BOX', (3, 0), (3, -1), 0.5, MID_GRAY),
        ('TOPPADDING', (0, 0), (-1, 0), 6),
    ]))
    elements.append(Spacer(1, 4*mm))
    elements.append(stat_table)
    elements.append(Spacer(1, 6*mm))

    # Defect summary table
    if defects_found:
        elements.append(Paragraph("Defects Detected:", bold_body))

        hdr_style = ParagraphStyle('TH', fontName='Helvetica-Bold', fontSize=8.5, textColor=WHITE)
        td_style = ParagraphStyle('TD', fontName='Helvetica', fontSize=8.5, textColor=DARK_GRAY)
        td_bold = ParagraphStyle('TDBold', fontName='Helvetica-Bold', fontSize=8.5, textColor=DARK_GRAY)

        table_data = [[
            Paragraph("#", hdr_style),
            Paragraph("Defect Type", hdr_style),
            Paragraph("Count", hdr_style),
            Paragraph("RPN", hdr_style),
            Paragraph("Severity", hdr_style),
            Paragraph("Surface Visible", hdr_style),
            Paragraph("Accuraccy", hdr_style),
        ]]

        for i, d in enumerate(sorted(defects_found,
                                       key=lambda x: DEFECT_DATABASE.get(x['type'], {}).get('rpn', 0),
                                       reverse=True), 1):
            db = DEFECT_DATABASE.get(d['type'], {})
            sev = db.get('severity', 'UNKNOWN')
            sev_cell = Paragraph(f"<font color='{severity_color(sev).hexval()}'><b>{sev}</b></font>", td_style)
            table_data.append([
                Paragraph(str(i), td_style),
                Paragraph(d['type'], td_bold),
                Paragraph(str(d['count']), td_style),
                Paragraph(str(db.get('rpn', 'N/A')), td_style),
                sev_cell,
                Paragraph("Yes" if db.get('surface_visible', True) else "Internal", td_style),
                Paragraph(f"{d.get('avg_confidence', 'N/A')}%", td_style),
            ])

        summary_table = Table(table_data, colWidths=[8*mm, 35*mm, 15*mm, 15*mm, 25*mm, 28*mm, 25*mm])
        summary_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), NAVY),
            ('TEXTCOLOR', (0, 0), (-1, 0), WHITE),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 0.5, MID_GRAY),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [WHITE, LIGHT_GRAY]),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ]))
        elements.append(summary_table)
    else:
        elements.append(Paragraph("No defects were detected during this scan. The weld appears to meet visual acceptance criteria.", body))

    elements.append(PageBreak())
    return elements

# ─────────────────────────────────────────────────────────────────────────────
# SECTION: DETAILED DEFECT FINDINGS
# ─────────────────────────────────────────────────────────────────────────────
def build_defect_details(scan_data, defects_found):
    elements = []

    elements.append(Spacer(1, 18*mm))
    elements.append(section_heading("2. DETAILED DEFECT FINDINGS"))

    body = ParagraphStyle('Body', fontName='Helvetica', fontSize=9, textColor=DARK_GRAY,
                           leading=13, spaceAfter=2*mm, alignment=TA_JUSTIFY)
    bold_body = ParagraphStyle('BoldBody', fontName='Helvetica-Bold', fontSize=9,
                                textColor=NAVY, spaceAfter=1*mm)
    small = ParagraphStyle('Small', fontName='Helvetica', fontSize=8, textColor=DARK_GRAY,
                            leading=11, spaceAfter=1*mm)

    if not defects_found:
        elements.append(Paragraph("No defects detected. This section is intentionally left brief.", body))
        elements.append(PageBreak())
        return elements

    industry = scan_data.get('industry', 'General')

    for idx, defect in enumerate(sorted(defects_found,
                                          key=lambda x: DEFECT_DATABASE.get(x['type'], {}).get('rpn', 0),
                                          reverse=True), 1):
        db = DEFECT_DATABASE.get(defect['type'], {})
        sev = db.get('severity', 'UNKNOWN')

        # Defect header with severity badge
        defect_title = ParagraphStyle('DefTitle', fontName='Helvetica-Bold', fontSize=12,
                                       textColor=NAVY, spaceAfter=1*mm)

        sev_badge_style = ParagraphStyle('Badge', fontName='Helvetica-Bold', fontSize=9,
                                          textColor=WHITE, alignment=TA_CENTER)

        header_data = [[
            Paragraph(f"2.{idx}  {defect['type']}", defect_title),
            Paragraph(sev, sev_badge_style),
            Paragraph(f"RPN: {db.get('rpn', 'N/A')}", ParagraphStyle('RPN', fontName='Helvetica-Bold',
                                                                       fontSize=9, textColor=NAVY, alignment=TA_CENTER)),
        ]]
        header_table = Table(header_data, colWidths=[100*mm, 30*mm, 30*mm])
        header_table.setStyle(TableStyle([
            ('BACKGROUND', (1, 0), (1, 0), severity_color(sev)),
            ('BACKGROUND', (2, 0), (2, 0), LIGHT_GRAY),
            ('ALIGN', (1, 0), (-1, 0), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('BOX', (0, 0), (-1, -1), 0.5, MID_GRAY),
        ]))
        elements.append(Spacer(1, 4*mm))
        elements.append(header_table)
        elements.append(Spacer(1, 2*mm))

        # Description
        elements.append(Paragraph("<b>Description:</b>", bold_body))
        elements.append(Paragraph(db.get('description', 'N/A'), body))

        # Detection details
        elements.append(Paragraph("<b>Detection Details:</b>", bold_body))
        det_data = [
            ["Instances Detected:", str(defect['count'])],
            ["Accuraccy:", f"{defect.get('avg_confidence', 'N/A')}%"],
            ["Surface Visible:", "Yes" if db.get('surface_visible', True) else "Mostly Internal (detected via surface indicators)"],
        ]
        det_table = Table(det_data, colWidths=[40*mm, 120*mm])
        det_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 8.5),
            ('TEXTCOLOR', (0, 0), (-1, -1), DARK_GRAY),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('TOPPADDING', (0, 0), (-1, -1), 2),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
        ]))
        elements.append(det_table)
        elements.append(Spacer(1, 2*mm))

        # Primary causes
        elements.append(Paragraph("<b>Primary Causes:</b>", bold_body))
        elements.append(Paragraph(db.get('primary_causes', 'N/A'), small))

        # Annotated image placeholder
        elements.append(Spacer(1, 2*mm))
        # if defect.get('image_path') and os.path.exists(defect['image_path']):
        #     elements.append(Paragraph("<b>Annotated Detection Image:</b>", bold_body))
        #     img = Image(defect['image_path'], width=140*mm, height=80*mm)
        #     img.hAlign = 'CENTER'
        #     elements.append(img)

        if defect.get('image_path') and os.path.exists(defect['image_path']):
            elements.append(Paragraph("<b>Annotated Detection Image:</b>", bold_body))

            # Open original image and get its dimensions
            pil_img = PILImage.open(defect['image_path']).convert("RGB")
            orig_w, orig_h = pil_img.size

            # Create a square canvas (max dimension × max dimension) with white background
            max_side = max(orig_w, orig_h)
            square_img = PILImage.new("RGB", (max_side, max_side), (255, 255, 255))

            # Paste original centered on the square canvas
            paste_x = (max_side - orig_w) // 2
            paste_y = (max_side - orig_h) // 2
            square_img.paste(pil_img, (paste_x, paste_y))

            # Save to an in-memory buffer so we don't write a temp file
            img_buffer = io.BytesIO()
            square_img.save(img_buffer, format="JPEG", quality=95)
            img_buffer.seek(0)

            # Use 100×100 mm placeholder
            img = Image(img_buffer, width=100*mm, height=100*mm)
            img.hAlign = 'CENTER'
            elements.append(img)
        else:
            # Placeholder box
            elements.append(Paragraph("<b>Annotated Detection Image:</b>", bold_body))
            placeholder_data = [[Paragraph(
                "<font color='#999999'>[Annotated image with bounding box and confidence score will be inserted here by the software]</font>",
                ParagraphStyle('ph', fontName='Helvetica-Oblique', fontSize=9, textColor=MID_GRAY, alignment=TA_CENTER)
            )]]
            ph_table = Table(placeholder_data, colWidths=[160*mm], rowHeights=[50*mm])
            ph_table.setStyle(TableStyle([
                ('BOX', (0, 0), (-1, -1), 1, MID_GRAY),
                ('BACKGROUND', (0, 0), (-1, -1), LIGHT_GRAY),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ]))
            elements.append(ph_table)

        elements.append(Spacer(1, 3*mm))

        # Standards reference
        elements.append(Paragraph("<b>Applicable Standards:</b>", bold_body))
        elements.append(Paragraph(db.get('standards_ref', 'N/A'), small))

        # Recommended action
        elements.append(Paragraph("<b>Recommended Action:</b>", bold_body))
        elements.append(Paragraph(db.get('recommended_action', 'N/A'), body))

        elements.append(Spacer(1, 2*mm))
        elements.append(HRFlowable(width="100%", thickness=0.5, color=MID_GRAY, spaceAfter=2*mm))

        elements.append(PageBreak())
        return elements

    elements.append(PageBreak())
    return elements

# ─────────────────────────────────────────────────────────────────────────────
# SECTION: INDUSTRY CRITICALITY ASSESSMENT
# ─────────────────────────────────────────────────────────────────────────────
def build_criticality_assessment(scan_data, defects_found):
    elements = []

    elements.append(Spacer(1, 18*mm))
    elements.append(section_heading("3. INDUSTRY CRITICALITY ASSESSMENT"))

    body = ParagraphStyle('Body', fontName='Helvetica', fontSize=9, textColor=DARK_GRAY,
                           leading=13, spaceAfter=3*mm, alignment=TA_JUSTIFY)
    bold_body = ParagraphStyle('BoldBody', fontName='Helvetica-Bold', fontSize=9.5,
                                textColor=NAVY, spaceAfter=2*mm)
    small = ParagraphStyle('Small', fontName='Helvetica', fontSize=8.5, textColor=DARK_GRAY,
                            leading=12, spaceAfter=2*mm, alignment=TA_JUSTIFY)

    industry = scan_data.get('industry', 'General')

    elements.append(Paragraph(
        f"This section evaluates the criticality of each detected defect in the context of "
        f"<b>{industry}</b> applications. The Risk Priority Number (RPN) ranking and industry-specific "
        f"severity ratings are derived from established welding quality standards (ISO 5817, AWS D1.1, "
        f"API 1104, ASME BPVC) and published research on defect criticality across industrial sectors.",
        body
    ))

    if not defects_found:
        elements.append(Paragraph("No defects detected - criticality assessment not applicable.", body))
        elements.append(PageBreak())
        return elements

    # Industry-specific criticality table
    industries = ["Aerospace", "Oil & Gas", "Automotive", "Construction", "Shipbuilding"]
    hdr_style = ParagraphStyle('TH', fontName='Helvetica-Bold', fontSize=7.5, textColor=WHITE, alignment=TA_CENTER)
    td_style = ParagraphStyle('TD', fontName='Helvetica', fontSize=7.5, textColor=DARK_GRAY, alignment=TA_CENTER)

    table_data = [[Paragraph("Defect", hdr_style)] + [Paragraph(ind, hdr_style) for ind in industries]]

    for defect in sorted(defects_found,
                          key=lambda x: DEFECT_DATABASE.get(x['type'], {}).get('rpn', 0),
                          reverse=True):
        db = DEFECT_DATABASE.get(defect['type'], {})
        row = [Paragraph(f"<b>{defect['type']}</b>", ParagraphStyle('td', fontName='Helvetica-Bold',
                                                                       fontSize=7.5, textColor=DARK_GRAY))]
        for ind in industries:
            crit = db.get('industry_criticality', {}).get(ind, ("N/A", ""))
            sev_text = crit[0] if isinstance(crit, tuple) else crit
            sc = severity_color(sev_text)
            row.append(Paragraph(f"<font color='{sc.hexval()}'><b>{sev_text}</b></font>", td_style))
        table_data.append(row)

    crit_table = Table(table_data, colWidths=[30*mm] + [26*mm]*5)
    crit_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), NAVY),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('GRID', (0, 0), (-1, -1), 0.5, MID_GRAY),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [WHITE, LIGHT_GRAY]),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    elements.append(crit_table)
    elements.append(Spacer(1, 5*mm))

    # Detailed industry-specific commentary for the selected industry
    elements.append(Paragraph(f"Detailed Assessment for <b>{industry}</b> Application:", bold_body))

    for defect in sorted(defects_found,
                          key=lambda x: DEFECT_DATABASE.get(x['type'], {}).get('rpn', 0),
                          reverse=True):
        db = DEFECT_DATABASE.get(defect['type'], {})
        crit_info = db.get('industry_criticality', {}).get(industry, None)

        if crit_info and isinstance(crit_info, tuple):
            sev_text, commentary = crit_info
        else:
            sev_text = "N/A"
            commentary = "No specific assessment available for this industry."

        sc = severity_color(sev_text)
        elements.append(Paragraph(
            f"<font color='{sc.hexval()}'><b>[{sev_text}]</b></font> "
            f"<b>{defect['type']}:</b> {commentary}",
            small
        ))

    elements.append(Spacer(1, 5*mm))

    # Severity legend
    elements.append(Paragraph("<b>Severity Legend:</b>", bold_body))
    legend_data = [
        [colored_box(RED_CRIT), Paragraph("<b>CRITICAL</b> - Immediate action required. Defect poses risk of structural failure or safety hazard.", small)],
        [colored_box(AMBER_HIGH), Paragraph("<b>HIGH</b> - Repair strongly recommended. Defect significantly reduces structural integrity or service life.", small)],
        [colored_box(YELLOW_MED), Paragraph("<b>MEDIUM</b> - Evaluate against acceptance criteria. May be acceptable within specified limits.", small)],
        [colored_box(GREEN_LOW), Paragraph("<b>LOW</b> - Generally acceptable. Monitor or address per workmanship standards.", small)],
    ]
    legend_table = Table(legend_data, colWidths=[8*mm, 155*mm])
    legend_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 2),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
    ]))
    elements.append(legend_table)

    elements.append(PageBreak())
    return elements

# ─────────────────────────────────────────────────────────────────────────────
# SECTION: RECOMMENDATIONS
# ─────────────────────────────────────────────────────────────────────────────
def build_recommendations(scan_data, defects_found):
    elements = []

    elements.append(Spacer(1, 18*mm))
    elements.append(section_heading("4. RECOMMENDATIONS & DISPOSITION"))

    body = ParagraphStyle('Body', fontName='Helvetica', fontSize=9.5, textColor=DARK_GRAY,
                           leading=14, spaceAfter=3*mm, alignment=TA_JUSTIFY)
    bold_body = ParagraphStyle('BoldBody', fontName='Helvetica-Bold', fontSize=9.5,
                                textColor=NAVY, spaceAfter=2*mm)

    if not defects_found:
        elements.append(Paragraph(
            "No defects were detected. The weld meets visual acceptance criteria based on AI inspection. "
            "It is recommended to verify with supplementary NDT methods as required by the applicable code or standard.",
            body
        ))
    else:
        # Determine overall recommendation
        max_sev = max(severity_rank(DEFECT_DATABASE.get(d['type'], {}).get('severity', 'LOW'))
                      for d in defects_found)

        if max_sev >= 4:
            overall = "REJECT - IMMEDIATE REPAIR REQUIRED"
            overall_color = RED_CRIT
            overall_text = (
                "One or more CRITICAL severity defects have been detected. The weld does not meet acceptance criteria "
                "and requires immediate repair. All critical defects must be completely removed and the area re-welded "
                "before the joint can be placed in service. Supplementary NDT (UT/RT/MT/PT) is recommended after repair "
                "to verify defect removal and repair quality."
            )
        elif max_sev >= 3:
            overall = "CONDITIONAL ACCEPT - REPAIR RECOMMENDED"
            overall_color = AMBER_HIGH
            overall_text = (
                "One or more HIGH severity defects have been detected. The weld should be evaluated against the applicable "
                "acceptance standard. Repair is recommended for defects exceeding acceptance limits. An engineering assessment "
                "may be required to determine fitness-for-service."
            )
        elif max_sev >= 2:
            overall = "CONDITIONAL ACCEPT - EVALUATE PER STANDARD"
            overall_color = YELLOW_MED
            overall_text = (
                "MEDIUM severity defects have been detected. These should be evaluated against the applicable acceptance "
                "criteria (ISO 5817, AWS D1.1, etc.). Defects within acceptance limits may be documented and accepted. "
                "Those exceeding limits require repair."
            )
        else:
            overall = "ACCEPT - MONITOR"
            overall_color = GREEN_LOW
            overall_text = (
                "Only LOW severity defects have been detected. These are generally acceptable under most welding standards "
                "and do not significantly affect structural integrity. Document findings and proceed."
            )

        # Disposition banner
        disp_style = ParagraphStyle('Disp', fontName='Helvetica-Bold', fontSize=13,
                                     textColor=WHITE, alignment=TA_CENTER)
        disp_data = [[Paragraph(overall, disp_style)]]
        disp_table = Table(disp_data, colWidths=[165*mm], rowHeights=[12*mm])
        disp_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), overall_color),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        elements.append(disp_table)
        elements.append(Spacer(1, 4*mm))
        elements.append(Paragraph(overall_text, body))
        elements.append(Spacer(1, 3*mm))

        # Per-defect recommendations
        elements.append(Paragraph("Per-Defect Recommendations:", bold_body))
        for defect in sorted(defects_found,
                              key=lambda x: DEFECT_DATABASE.get(x['type'], {}).get('rpn', 0),
                              reverse=True):
            db = DEFECT_DATABASE.get(defect['type'], {})
            sev = db.get('severity', 'UNKNOWN')
            sc = severity_color(sev)
            elements.append(Paragraph(
                f"<font color='{sc.hexval()}'><b>[{sev}]</b></font> <b>{defect['type']}:</b> "
                f"{db.get('recommended_action', 'Evaluate per applicable standard.')}",
                body
            ))

    elements.append(Spacer(1, 8*mm))

    # Supplementary NDT recommendation
    elements.append(Paragraph("Supplementary NDT Recommendation:", bold_body))
    elements.append(Paragraph(
        "This report is based on AI-powered visual inspection only. For a complete assessment, "
        "the following supplementary non-destructive testing methods are recommended based on the defects detected:",
        body
    ))

    ndt_recs = set()
    for d in defects_found:
        db = DEFECT_DATABASE.get(d['type'], {})
        if not db.get('surface_visible', True):
            ndt_recs.add("Radiographic Testing (RT)")
            ndt_recs.add("Ultrasonic Testing (UT)")
        if d['type'] in ['Crack', 'Lack of Fusion', 'Arc Strike']:
            ndt_recs.add("Magnetic Particle Testing (MT)")
            ndt_recs.add("Liquid Penetrant Testing (PT)")
        if d['type'] in ['Porosity', 'Slag Inclusion']:
            ndt_recs.add("Radiographic Testing (RT)")

    if not ndt_recs:
        ndt_recs = {"Visual re-inspection by certified inspector recommended"}

    for ndt in sorted(ndt_recs):
        elements.append(Paragraph(f"  \u2022  {ndt}", body))

    elements.append(Spacer(1, 8*mm))

    # Sign-off section
    elements.append(Paragraph("Sign-Off:", bold_body))
    signoff_data = [
        [Paragraph("<b>Inspector Name:</b>", body), Paragraph("_________________________", body),
         Paragraph("<b>Date:</b>", body), Paragraph("_____________", body)],
        [Paragraph("<b>Signature:</b>", body), Paragraph("_________________________", body),
         Paragraph("<b>Qualification:</b>", body), Paragraph("_____________", body)],
        [Paragraph("<b>Reviewed By:</b>", body), Paragraph("_________________________", body),
         Paragraph("<b>Date:</b>", body), Paragraph("_____________", body)],
    ]
    signoff_table = Table(signoff_data, colWidths=[30*mm, 55*mm, 30*mm, 45*mm])
    signoff_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'BOTTOM'),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    elements.append(signoff_table)

    elements.append(PageBreak())
    return elements

# ─────────────────────────────────────────────────────────────────────────────
# SECTION: APPENDIX - DEFECT REFERENCE
# ─────────────────────────────────────────────────────────────────────────────
def build_appendix():
    elements = []

    elements.append(Spacer(1, 18*mm))
    elements.append(section_heading("APPENDIX A: WELD DEFECT REFERENCE GUIDE"))

    body = ParagraphStyle('Body', fontName='Helvetica', fontSize=8, textColor=DARK_GRAY,
                           leading=11, spaceAfter=2*mm)
    bold_body = ParagraphStyle('BoldBody', fontName='Helvetica-Bold', fontSize=8,
                                textColor=NAVY, spaceAfter=1*mm)

    elements.append(Paragraph(
        "This appendix provides a quick reference for all weld defects recognized by the AI detection system, "
        "ranked by Risk Priority Number (RPN). RPN values are based on severity, occurrence probability, "
        "and detection difficulty in safety-critical industrial applications.",
        body
    ))
    elements.append(Spacer(1, 3*mm))

    hdr_style = ParagraphStyle('TH', fontName='Helvetica-Bold', fontSize=7, textColor=WHITE, alignment=TA_CENTER)
    td_style = ParagraphStyle('TD', fontName='Helvetica', fontSize=7, textColor=DARK_GRAY, alignment=TA_CENTER)
    td_left = ParagraphStyle('TDL', fontName='Helvetica', fontSize=7, textColor=DARK_GRAY)

    table_data = [[
        Paragraph("Rank", hdr_style),
        Paragraph("Defect", hdr_style),
        Paragraph("RPN", hdr_style),
        Paragraph("Severity", hdr_style),
        Paragraph("Visible", hdr_style),
        Paragraph("AI Detect.", hdr_style),
        Paragraph("Primary Cause", hdr_style),
    ]]

    ai_detect_map = {
        "Crack": "Very Easy", "Porosity": "Easy", "Lack of Fusion": "Hard",
        "Lack of Penetration": "Hard", "Undercut": "Very Easy", "Spatter": "Easy",
        "Burn Through": "Easy", "Overlap": "Easy", "Slag Inclusion": "Very Hard",
        "Mechanical Mark": "Easy", "Underfill": "Easy", "Arc Strike": "Easy",
        "Tack Weld": "Easy", "Excess Penetration": "Easy", "Suck Back": "Medium",
    }

    sorted_defects = sorted(DEFECT_DATABASE.items(), key=lambda x: x[1].get('rpn', 0), reverse=True)
    for rank, (name, db) in enumerate(sorted_defects, 1):
        sev = db.get('severity', 'UNKNOWN')
        sc = severity_color(sev)
        causes = db.get('primary_causes', 'N/A')
        if len(causes) > 60:
            causes = causes[:57] + "..."
        table_data.append([
            Paragraph(str(rank), td_style),
            Paragraph(f"<b>{name}</b>", td_left),
            Paragraph(str(db.get('rpn', 'N/A')), td_style),
            Paragraph(f"<font color='{sc.hexval()}'><b>{sev}</b></font>", td_style),
            Paragraph("Yes" if db.get('surface_visible') else "No", td_style),
            Paragraph(ai_detect_map.get(name, "N/A"), td_style),
            Paragraph(causes, td_left),
        ])

    ref_table = Table(table_data, colWidths=[10*mm, 28*mm, 12*mm, 18*mm, 12*mm, 18*mm, 62*mm])
    ref_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), NAVY),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('ALIGN', (1, 1), (1, -1), 'LEFT'),
        ('ALIGN', (6, 1), (6, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('GRID', (0, 0), (-1, -1), 0.5, MID_GRAY),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [WHITE, LIGHT_GRAY]),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ('FONTSIZE', (0, 0), (-1, -1), 7),
    ]))
    elements.append(ref_table)

    elements.append(Spacer(1, 6*mm))
    elements.append(Paragraph("<b>Disclaimer:</b>", bold_body))
    elements.append(Paragraph(
        "This report is generated by an AI-powered visual inspection system and should be used as a screening tool only. "
        "Final disposition decisions must be made by a qualified welding inspector in accordance with applicable codes and standards. "
        "The AI system processes surface-visible features only and cannot detect internal (subsurface) defects unless "
        "they manifest as surface indicators. Supplementary NDT methods are recommended for comprehensive assessment.",
        body
    ))

    return elements

# ─────────────────────────────────────────────────────────────────────────────
# HELPER FUNCTIONS
# ─────────────────────────────────────────────────────────────────────────────
def section_heading(text):
    style = ParagraphStyle('SectionHead', fontName='Helvetica-Bold', fontSize=14,
                            textColor=NAVY, spaceAfter=2*mm, spaceBefore=2*mm)
    return KeepTogether([
        Paragraph(text, style),
        HRFlowable(width="100%", thickness=1.5, color=ACCENT, spaceAfter=4*mm),
    ])

def colored_box(color):
    d = Drawing(6*mm, 4*mm)
    d.add(Rect(0, 0, 6*mm, 4*mm, fillColor=color, strokeColor=None))
    return d

# ─────────────────────────────────────────────────────────────────────────────
# MAIN REPORT GENERATOR
# ─────────────────────────────────────────────────────────────────────────────
def generate_report(scan_data, defects_found, output_path="weld_scan_report.pdf"):
    """
    Generate a complete weld defect inspection report.

    Args:
        scan_data (dict): Metadata about the scan. Keys include:
            - report_id, sample_id, scan_number, scan_date, operator_name,
            - location, specimen_type, joint_config, material, specimen_size,
            - welding_process, industry, standard, model_version, device,
            - company_name, scan_side, confidence_avg, overall_verdict

        defects_found (list[dict]): List of detected defects. Each dict:
            - type (str): Defect type name (must match DEFECT_DATABASE keys)
            - count (int): Number of instances
            - avg_confidence (float): Average detection confidence %
            - locations (str): Description of locations
            - image_path (str, optional): Path to annotated image

        output_path (str): Output PDF file path.
    """
    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        leftMargin=15*mm,
        rightMargin=15*mm,
        topMargin=32*mm,
        bottomMargin=18*mm,
    )

    page_template = ReportPageTemplate(scan_data)
    story = []

    # Build all sections
    story.extend(build_cover_page(scan_data))
    story.extend(build_scan_summary(scan_data, defects_found))
    story.extend(build_defect_details(scan_data, defects_found))
    # story.extend(build_criticality_assessment(scan_data, defects_found))
    # story.extend(build_recommendations(scan_data, defects_found))
    # story.extend(build_appendix())

    # Build the PDF
    doc.build(story, onFirstPage=lambda c, d: None,  # Cover page has no header
              onLaterPages=page_template.header_footer)

    print(f"Report generated: {output_path}")
    return output_path


# ─────────────────────────────────────────────────────────────────────────────
# DEMO: Generate a sample report with realistic data
# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    # Sample scan data (this would come from your application)
    scan_data = {
        "report_id": "RPT-2026-00042",
        "sample_id": "VT-2961",
        "scan_number": 7,
        "scan_date": "12 Apr 2026, 14:35",
        "operator_name": "Rajesh Kumar",
        "location": "Welding Bay 3, Plant A - Pune",
        "specimen_type": "Pipe / Cylindrical",
        "joint_config": "Single V Butt Joint (Plate)",
        "material": "Stainless Steel",
        "specimen_size": "300 x 300 x 8mm",
        "welding_process": "SMAW (Shielded Metal Arc Welding)",
        "industry": "Oil & Gas",
        "standard": "ISO 5817 Level B / API 1104",
        "model_version": "v1",
        "device": "Handheld Inspection Unit (12MP, f/1.8)",
        "company_name": "WeldVision AI",
        "scan_side": "CAP",
        "confidence_avg": 87.3,
        "overall_verdict": "DEFECTS DETECTED",
    }

    # Sample defects detected (this would come from your YOLOv8 model output)
    defects_found = [
        {
            "type": "Porosity",
            "count": 3,
            "avg_confidence": 92.1,
            "locations": "29mm from datum (16mm length), Cluster pattern at cap side",
            "image_path": "/content/defect-sample.png",  # Will show placeholder
        }
        # {
        #     "type": "Undercut",
        #     "count": 2,
        #     "avg_confidence": 88.5,
        #     "locations": "236mm from datum (19mm length), Side A of weld toe",
        #     "image_path": "/content/defect-sample.png",
        # },
        # {
        #     "type": "Lack of Fusion",
        #     "count": 1,
        #     "avg_confidence": 78.2,
        #     "locations": "99mm from datum (17mm length), Root side - Side A",
        #     "image_path": "/content/defect-sample.png",
        # },
        # {
        #     "type": "Burn Through",
        #     "count": 1,
        #     "avg_confidence": 85.6,
        #     "locations": "138mm from datum (3mm length), Root side",
        #     "image_path": "/content/defect-sample.png",
        # },
        # {
        #     "type": "Spatter",
        #     "count": 4,
        #     "avg_confidence": 94.8,
        #     "locations": "Multiple locations along weld bead, both sides",
        #     "image_path": "/content/defect-sample.png",
        # },
    ]

    output = generate_report(scan_data, defects_found, "/content/weld_report.pdf")
